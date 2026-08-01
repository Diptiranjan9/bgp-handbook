## BGP Filtering

> 💡 **TL;DR:** BGP filtering controls which routes you accept from a peer and which you advertise to them — done through **prefix-lists** (match on IP+mask), **AS-PATH filters** (match on AS_PATH regex), **route-maps** (combine matches + modify attributes), and **communities** (tag-based policy). Filtering isn't optional in production — it prevents route leaks, accidental transit, and prefix hijacking.

Related: [[BGP Community]] · [[BGP Aggregation]] · [[BGP Path Selection]]

References: [Cisco/APNIC ISP Workshop — BGP Route Filtering Lab](https://bgp4all.com/pfs/_media/workshops/07-bgp-route-filtering.pdf) · [OneUptime — Implementing BGP Route Filtering](https://oneuptime.com/blog/post/2026-01-30-bgp-route-filtering/view)

---

### Why Filtering Matters

- **Route leaks** — accidentally re-advertising a learned route turns your network into unintended transit.
- **Prefix hijacking** — accepting bogus announcements can redirect traffic through malicious networks.
- **Table bloat** — accepting a full routing table you don't need wastes memory/CPU.
- **Peering/IXP policy compliance** — many peering agreements mandate specific filtering.

> 📝 **General rule:** Always filter in **both directions** — inbound protects your own routing table from bad peer behavior, outbound protects your peers from your own misconfiguration.

---

### 1. Prefix-List Filtering

The simplest, most direct method — matches routes purely on **IP prefix + mask length**, no attribute inspection needed.

**Use cases:**
- Accept only specific customer-owned prefixes
- Block bogon (reserved/private) address space
- Reject overly specific announcements (e.g., anything longer than /24)

```cisco
ip prefix-list CUSTOMER-PREFIXES seq 10 permit 203.0.113.0/24
ip prefix-list CUSTOMER-PREFIXES seq 20 permit 198.51.100.0/24 le 25

! Common bogon block
ip prefix-list BOGON-FILTER seq 10 deny 10.0.0.0/8 le 32
ip prefix-list BOGON-FILTER seq 20 deny 172.16.0.0/12 le 32
ip prefix-list BOGON-FILTER seq 30 deny 192.168.0.0/16 le 32
ip prefix-list BOGON-FILTER seq 1000 permit 0.0.0.0/0 le 24

router bgp 65001
 neighbor 192.0.2.1 remote-as 64501
 neighbor 192.0.2.1 prefix-list BOGON-FILTER in
 neighbor 192.0.2.1 prefix-list CUSTOMER-PREFIXES out
```

> ⚠️ **Gotcha:** An IOS prefix-list has an **implicit `deny any`** at the end even though it's not shown — anything not explicitly permitted is dropped. Some ISPs add it explicitly anyway as a documented security precaution.

> 📝 **Granularity note:** Prefix-lists match only what a neighbor **originates or is authorized for** — this is more precise than AS-PATH filtering, which (as shown next) lets through *every* prefix originated anywhere in a matched AS, not just a specific block.

---

### 2. AS-PATH Filtering

Matches based on the **AS_PATH attribute** using regular expressions — controls routes based on which ASes they've traversed, not their IP value.

| Regex Pattern | Meaning |
|---|---|
| `^$` | Route originated **locally** (empty AS_PATH) |
| `^64501$` | Route originated **by** AS 64501 |
| `_64501_` | Route passes through AS 64501 **anywhere** in the path |
| `^64501_` | AS 64501 is the **first** AS in the path (i.e., your directly connected peer) |
| `_64501$` | AS 64501 is the **last** AS before you |
| `^[0-9]+$` | Single-hop / directly originated routes only |

```cisco
ip as-path access-list 2 permit ^$
ip as-path access-list 3 permit ^10$
!
router bgp 40
 neighbor 10.40.15.18 remote-as 10
 neighbor 10.40.15.18 filter-list 2 out
 neighbor 10.40.15.18 filter-list 3 in
```

> ⚠️ **Gotcha — why outbound filters match `^$` not your own ASN:** The AS_PATH attribute is only set (prepended with your own AS) **after** prefix-lists, AS-path filters, and route-maps are evaluated on outbound. If you tried matching your own AS number in an outbound filter-list, it would never match at that stage — hence outbound filters match the *pre-prepend* state (`^$` = "not yet touched" = locally originated).

> ⚠️ **Less granular than prefix-lists:** An AS-PATH filter matching `^64501$` lets through **every prefix** that AS originates — you can't restrict to a specific subnet within that AS the way a prefix-list can. Prefix-lists are generally preferred for precision; AS-PATH filters are useful when you don't know or can't track every specific prefix an AS might originate.

---

### 3. Route-Maps — Combining Everything

Route-maps are the most flexible mechanism: they **combine multiple match conditions** (prefix-list, AS-PATH, community) in sequential numbered clauses, and can also **modify attributes** (local-pref, MED, community, next-hop) on match — not just permit/deny.

**Processing logic:** clauses are evaluated in order; first match wins; if nothing matches, there's an **implicit deny** at the end (like ACLs).

```cisco
ip prefix-list ALLOWED-PREFIXES seq 10 permit 203.0.113.0/24
ip as-path access-list 10 permit ^64501$
ip community-list standard CUSTOMER-ROUTES permit 65001:100

route-map INBOUND-POLICY permit 10
 match ip address prefix-list ALLOWED-PREFIXES
 match as-path 10
 set local-preference 150
 set community 65001:100 additive

route-map INBOUND-POLICY deny 100
 description Deny everything else

router bgp 65001
 neighbor 192.0.2.1 route-map INBOUND-POLICY in
```

> 📝 **Gotcha:** If you forget the final explicit deny/permit clause and rely only on the implicit deny, it's easy to accidentally block routes you meant to allow through — always add an explicit final `permit` catch-all clause if the intent is "match specific things, allow everything else through unchanged."

---

### 4. Community-Based Filtering

Instead of maintaining prefix-lists or AS-PATH filters per neighbor, tag routes once with a **community**, then filter/act on the tag downstream — this is what makes community-based policy scale so well (see [[BGP Community]] for the full deep dive).

```cisco
ip bgp-community new-format
!
ip prefix-list out-match permit 10.30.0.0/20 le 26
!
route-map outfilter permit 10
 match ip address prefix-list out-match
 set community 30:8
!
router bgp 30
 neighbor 10.20.15.17 remote-as 20
 neighbor 10.20.15.17 route-map outfilter out
 neighbor 10.20.15.17 send-community
```

**Receiving side — match community and act:**
```cisco
ip community-list 3 permit 10:1
!
route-map infilter permit 10
 match community 3
 set local-preference 120
route-map infilter permit 20
 ! catch-all: pass everything else at default local-pref
```

> ⚠️ **Gotcha (critical, comes up constantly):** BGP does **not send communities by default** — you must explicitly configure `neighbor <ip> send-community` on **both** the eBGP and iBGP sides, or the community attribute is silently stripped and downstream matching just fails with no obvious error.

> 📝 **Community format:** Standard communities are 32-bit, conventionally split into two 16-bit fields — `ASN:VALUE`. The exceptions are well-known strings like `no-export` and `no-advertise`, which aren't ASN-specific.

> 📝 **Outbound scrubbing:** In production, ISPs typically **strip internal/customer-facing communities before advertising further upstream**, so internal signaling doesn't leak to the wider internet:
```cisco
route-map OUTBOUND-SCRUB permit 10
 set comm-list INTERNAL delete
```

---

### 5. RPKI-Based Filtering (Route Origin Validation)

Adds **cryptographic validation** — checks whether the originating AS is actually authorized to announce a given prefix, using Route Origin Authorizations (ROAs) from RPKI.

| Validation State | Meaning | Typical Action |
|---|---|---|
| **Valid** | ROA exists and matches AS + prefix | Accept, often with higher local-pref |
| **Invalid** | ROA exists but doesn't match (wrong AS or prefix) | Reject — likely hijack or misconfig |
| **NotFound** | No ROA published for this prefix | Accept, but with lower/default preference |

```cisco
router bgp 65001
 bgp rpki server tcp 192.0.2.100 port 8282 refresh 300

route-map RPKI-POLICY permit 10
 match rpki valid
 set local-preference 200
route-map RPKI-POLICY permit 20
 match rpki not-found
 set local-preference 100
route-map RPKI-POLICY deny 30
 match rpki invalid

router bgp 65001
 neighbor 192.0.2.1 route-map RPKI-POLICY in
```

> 💡 **Why it matters:** RPKI is the modern answer to prefix hijacking — AS-PATH and prefix-list filters trust that the announcing AS is telling the truth about ownership; RPKI cryptographically verifies it instead.

---

### 6. Maximum Prefix Limits

Protects against memory exhaustion or a misbehaving/compromised peer suddenly announcing far more routes than expected.

```cisco
router bgp 65001
 ! Warn only, don't tear down session
 neighbor 192.0.2.1 maximum-prefix 1000 75 warning-only
 ! Shut the session down if exceeded, auto-restart after 30 min
 neighbor 192.0.2.2 maximum-prefix 5000 80 restart 30
```

> ⚠️ **Gotcha:** Set this appropriately per peer relationship — a full-table transit peer needs a limit sized well above the current global IPv4 table size (~900k+ prefixes), while a single-homed customer peer should have a tight limit matching what they're expected to announce.

---

### Filtering Order of Operations (Typical Inbound Chain)

```text
BGP Update In
   → RPKI Validation
   → Prefix-List (bogon filter)
   → Maximum-Prefix check
   → AS-Path Filter
   → Community Processing
   → Set Local Preference
   → Installed into BGP RIB
```

```text
BGP RIB
   → Outbound: only advertise owned/authorized prefixes
   → Strip internal communities
   → Add standard/public communities
   → AS-Path prepend (if TE requires it)
   → BGP Update Out
```

> 📝 **Defense in depth:** Production filters rarely rely on just one mechanism — combining prefix-lists (precision), AS-PATH filters (path-based sanity), communities (policy signaling), RPKI (cryptographic origin validation), and max-prefix (blast-radius control) gives layered protection where no single misconfiguration exposes the whole network.

---

### Verifying & Troubleshooting Filters

```cisco
! Compare what was received vs what was actually accepted after filtering
show ip bgp neighbors <ip> received-routes
show ip bgp neighbors <ip> routes

! Test a specific prefix against a prefix-list
show ip prefix-list BOGON-FILTER 10.0.0.0/8

! Test AS-path regex matches
show ip bgp regexp ^64501$

! Check RPKI validation state for a prefix
show ip bgp 203.0.113.0/24 rpki
```

> ⚠️ **Gotcha — policy changes need a refresh, not just a config change:** Entering new prefix-lists, AS-path filters, or route-maps only affects **future incremental BGP updates** — it does **not** retroactively re-evaluate routes already in the table. You must refresh the session for the new policy to apply to the existing table:
```cisco
clear ip bgp <neighbor-ip> in
clear ip bgp <neighbor-ip> out
```
> This relies on **Route Refresh capability (RFC 2918)** for a graceful refresh — omitting `in`/`out` performs a **hard reset**, tearing down the entire BGP session, which is disruptive and should be avoided on production peers.

---

### Quick Comparison

| Method | Matches On | Modifies Attributes? | Precision | Common Use |
|---|---|---|---|---|
| Prefix-List | IP prefix + mask | No | High | Bogon filtering, exact customer prefixes |
| AS-PATH Filter | AS_PATH regex | No | Medium | Block/allow entire AS's announcements |
| Route-Map | Any of the above, combined | **Yes** | High | Policy + attribute-setting in one place |
| Community Filter | Community tag | Indirectly (via matched route-map) | High (if tagging is precise) | Scalable, delegated policy signaling |
| RPKI | Cryptographic ROA | No (usually paired with route-map) | Highest (cryptographic) | Anti-hijacking |
| Max-Prefix | Count of prefixes | No (session action) | N/A | Blast-radius/DoS protection |