## BGP Only-to-Customer (OTC) Attribute & BGP Roles (RFC 9234)

> 💡 **TL;DR:** RFC 9234 fixes route leaks (a route learned from a provider/peer getting accidentally re-advertised to another provider/peer) by baking the AS relationship directly into BGP itself. Two eBGP neighbors each configure a **BGP Role** (Provider, Customer, Peer, RS, or RS-Client), confirm it in the OPEN message, and BGP automatically stamps routes with an **OTC (Only to Customer)** attribute once they've traveled sideways or downward. Once OTC is set, a compliant router will refuse to send that route anywhere except further downward to a customer — turning route-leak prevention from a manual, error-prone config exercise into something the protocol enforces on its own.

Related: [[BGP Attributes]] · [[BGP Filtering]] · [[BGP Path Selection]]

References: [RFC 9234 — Route Leak Prevention and Detection Using Roles in UPDATE and OPEN Messages](https://datatracker.ietf.org/doc/rfc9234/) · [Noction — BGP Route Leak Prevention via RFC 9234](https://www.noction.com/blog/bgp-route-leak) · [Cloudflare — BGP Role Model: Tracking the Adoption of RFC 9234](https://blog.cloudflare.com/rfc9234-bgp-role-model/)

---

## Why This Exists — The Route Leak Problem

- A **route leak** is a route propagating beyond its intended scope, based on the business/topology relationship between ASes (RFC 7908).
- The internet's implicit rule is the **valley-free property** (Gao-Rexford model): a route should only ever propagate **downward** — from provider → customer, or laterally between peers who only exchange their own/customer routes. It should never travel back **upward** again once it's gone down.
- A **route leak** happens when this gets violated — most classically a **hairpin leak**: a customer with two upstream providers accidentally re-advertises a route learned from Provider A to Provider B, creating a "valley" that was never authorized.

> ⚠️ **Why this matters:** A route leak isn't just a routing inefficiency — the leaking AS may not have the bandwidth capacity to carry transit traffic between its two providers, causing congestion, latency spikes, or in worse cases, traffic interception. Route leaks are also a **frequent, ongoing occurrence** on the internet — monitoring services have logged hundreds of distinct leak events across just a few months.

- **The old defense:** operators manually configure inbound/outbound route-maps and prefix-lists per session, based on their own understanding of the relationship — with **no in-band way to verify** the neighbor's configuration matches. One misconfigured or missing filter, and a leak happens.
- **RFC 9234's fix:** move this from "operator hopes both sides configured it correctly" to "the protocol negotiates and enforces it automatically."

---

## BGP Role

- A **BGP Role** declares where you sit relative to a specific eBGP neighbor, on that specific session.
- Configured **locally**, then advertised as a new **BGP Role Capability** (capability code 9) in the OPEN message — if both sides support RFC 9234, each confirms the other's declared Role during session establishment.

### The Five Roles

| Role | Meaning |
|---|---|
| **Provider** | The local AS is a transit provider of the remote AS |
| **Customer** | The local AS is a transit customer of the remote AS |
| **Peer** | Local and remote AS have a lateral (non-transit) peering relationship |
| **RS** (Route Server) | The local AS is a Route Server, usually at an IXP |
| **RS-Client** | The local AS is a client of an RS |

### Valid Role Pairings

Only these five pairings are valid on a given session — anything else is a **mismatch**:

| Local AS Role | Remote AS Role |
|---|---|
| Provider | Customer |
| Customer | Provider |
| RS | RS-Client |
| RS-Client | RS |
| Peer | Peer |

> ⚠️ **Role Mismatch = session rejected:** If both sides advertise a Role Capability and the pairing isn't one of the five above, the BGP session is **rejected** with a Role Mismatch Notification (error code 2, subcode 11). This is a *feature*, not a bug — a mismatch means the two networks fundamentally disagree about their relationship, which is exactly the kind of latent misunderstanding that would otherwise surface later as a route leak. Better to fail the handshake immediately than fail silently in production.

> 📝 **Partial deployment is handled gracefully:** if you send a Role Capability but your neighbor doesn't support RFC 9234 at all, the session **still comes up** — your locally configured Role still drives your own route-leak prevention logic unilaterally. An operator wanting a harder guarantee can enable **"strict mode,"** which rejects any session where the neighbor doesn't send a Role Capability at all — though this is opt-in and not yet realistic for most networks, since adoption is still uneven across the internet.

> ⚠️ **Complex relationships aren't allowed on one session:** if you hold more than one relationship type with the same neighbor (e.g., Provider-to-Customer for some prefixes, Peer-to-Peer for others, over a single session) — RFC 9234 explicitly says Roles **must not** be configured on that session at all. The fix is to split it into separate eBGP sessions, each with a single, clean relationship, and assign a Role to each individually.

---

## BGP Only-to-Customer (OTC) Attribute

- **Attribute Type Code 35**, Optional Transitive, carrying a single 4-byte value: an **AS number**.
- Purpose: once a route has been sent to a Customer, a Peer, or an RS-Client, OTC marks it so that it can **only continue downward to Customers from that point on** — never back up to a Provider, Peer, or RS.
- Being **transitive** matters a lot here: even a router with zero RFC 9234 support is still expected (per standard optional-transitive attribute handling, RFC 4271/RFC 7606) to pass OTC along unchanged rather than silently drop it — which is what lets non-adjacent, RFC 9234-compliant ASes several hops away still detect a leak using an OTC value set far upstream.

### Ingress Procedure (on route receipt)

| Condition | Action |
|---|---|
| Route with OTC received **from a Customer or RS-Client** | **Route leak** — mark route ineligible |
| Route with OTC received **from a Peer**, and OTC value ≠ that Peer's own ASN | **Route leak** — mark route ineligible |
| Route received **from a Provider, Peer, or RS**, and OTC is **not** present | **Add OTC**, value = remote AS's ASN |

### Egress Procedure (on route advertisement)

| Condition | Action |
|---|---|
| Advertising **to a Customer, Peer, or RS-Client**, and OTC not present | **Add OTC**, value = local AS's own ASN |
| Route **already carries OTC** | **Must NOT** be advertised to a Provider, Peer, or RS |

> 💡 **Why both ingress AND egress rules exist:** in a perfect world with universal RFC 9234 adoption, the egress rule alone would be enough — the sender stamps OTC as it sends downward. But during partial deployment, some senders won't be compliant yet, so the **ingress rule fills the gap**: the receiving Customer/Peer/RS-Client stamps OTC themselves if it's missing, using the *sender's* ASN as the value. Either side setting it produces the same result, which makes the mechanism more robust for early adopters even before everyone else catches up.

> ⚠️ **Once set, OTC is permanent for that route's life:** RFC 9234 requires that OTC, once attached, **must be preserved unchanged** as the route propagates further. Removing it or altering its value defeats the entire mechanism — and per Cloudflare's research (below), this is a real problem happening today, not just a theoretical risk.

---

## Worked Example — Applying Roles + OTC

**Topology:** Router R1 (AS 64502) is a customer of two providers, ISP1 (AS 64501) and ISP2 (AS 64503).

```txt
                    ISP1 (FRR, AS 64501)                 ISP2 (FRR, AS 64503)
                    Role: Provider                        Role: Provider
                    Originates: 100.100.100.0/24
                            |                                      |
                            | eBGP                                 | eBGP
                            | 192.168.1.1 <----> 192.168.1.2       | 192.168.2.1 <----> 192.168.2.2
                            |                                      |
                            +------------------+-------------------+
                                               |
                                        R1 (FRR, AS 64502)
                                        Role: Customer (toward both)

   Flow of the test prefix:
   ISP1 --[100.100.100.0/24, OTC=64501]--> R1   (accepted: from a Provider, OTC presence is fine)
   R1   --X (withheld) X-------------------> ISP2  (blocked: route already carries OTC, egress rule
                                                      forbids sending it to another Provider)
```

**R1 — configure Customer role toward both providers:**
```frr
router bgp 64502
   no bgp ebgp-requires-policy
   neighbor 192.168.1.1 remote-as 64501
   neighbor 192.168.1.1 local-role customer
   neighbor 192.168.2.1 remote-as 64503
   neighbor 192.168.2.1 local-role customer
```

**ISP1 — configure Provider role, and originate a test prefix:**
```frr
router bgp 64501
    no bgp ebgp-requires-policy
    neighbor 192.168.1.2 remote-as 64502
    neighbor 192.168.1.2 local-role provider

address-family ipv4 unicast
    network 100.100.100.0/24
    exit-address-family
```

**ISP2 — configure Provider role:**
```frr
router bgp 64503
   no bgp ebgp-requires-policy
   neighbor 192.168.2.2 remote-as 64502
   neighbor 192.168.2.2 local-role provider
```

**What happens:**
1. ISP1 (Role: Provider) sends `100.100.100.0/24` to R1 (Role: Customer), attaching **OTC = 64501** on the way out, since ISP1 is advertising to a Customer with no OTC present yet.
2. R1 receives the route. Since it came from a Provider, the presence of OTC is **not** treated as a leak — R1 installs it normally in its BGP table.
3. R1 now tries to consider whether to advertise `100.100.100.0/24` onward to ISP2. Since the route **already carries OTC**, the egress rule says it **must not** be sent to a Provider — so R1 correctly withholds it from ISP2, with zero manual route-map/prefix-list configuration needed.

> ⚠️ **What if the Roles are wrong?** If R1's local-role toward ISP1 were mistakenly set to `peer` instead of `customer` (breaking the valid Provider↔Customer pairing), the session would be **rejected outright** with a Role Mismatch Notification (code 2, subcode 11) — the two eBGP speakers simply cannot establish a connection until the mismatch is fixed. This immediate, visible failure is far easier to catch and fix than a silent leak discovered days later.

---

## Real-World Adoption — What Cloudflare's Research Found

Cloudflare ran a large-scale measurement study (using their global peering footprint and BMP feeds) to see how widely RFC 9234 has actually been adopted on the internet, and it revealed a few important findings:

- Roughly **67 ASes** were confirmed setting the OTC attribute correctly toward Cloudflare over a 3-month observation window, with **Route Servers at Internet Exchange Points** among the fastest adopters — likely because many run open-source BGP implementations that ship new RFCs faster.
- **Detecting who actually sets OTC is genuinely hard**, because of the dual ingress/egress stamping rule: seeing an AS_PATH like `64506 64507` with `OTC=64507` doesn't tell you whether 64507 set it themselves on egress, or 64506 filled it in on ingress. Cloudflare had to build multi-step inference methods (tracking which ASes reliably appear as "OTC setters" vs "OTC fillers-in" across many paths) just to estimate adoption.
- **The more concerning finding:** using a controlled announce/withdraw experiment with test prefixes, Cloudflare discovered that **two major Tier-1 networks were stripping the OTC attribute entirely** — meaning routes passing through them lost their leak-detection marker, silently defeating RFC 9234's protection for anyone downstream of them. Roughly **1 in 3 IPv4 AS_PATHs** observed in the experiment had OTC missing, and the two Tier-1s accounted for the overwhelming majority of that.
- Both networks confirmed this was a deliberate defensive practice, originally adopted to guard against older BGP implementations that used to **reset the entire session** upon receiving a malformed transitive attribute (a risk later fixed by RFC 7606's "treat-as-withdraw" error handling) — but stripping OTC as a blanket policy undermines the very mechanism meant to protect the internet from leaks.

> ⚠️ **Key takeaway:** RFC 9234 only works end-to-end if **every AS in the path preserves OTC**, even ones that don't understand or use it themselves (that's the whole point of it being "transitive"). A single large transit network stripping the attribute for outdated defensive reasons can silently break leak detection for everyone downstream, which is exactly why Cloudflare's research and outreach to those networks matters — protocol correctness alone isn't enough without real deployment discipline.

---

## Vendor Support (as of the Cloudflare study, August 2026)

| BGP Implementation | RFC 9234 Support |
|---|---|
| Cisco IOS XR | Coming in a future release |
| Junos OS / Junos OS Evolved | ✅ Yes |
| Arista EOS | ❌ No |
| Nokia SR OS | ❌ No |
| Huawei | ❌ No |
| Extreme SLX-OS | ❌ No |
| RouterOS | ✅ Yes |
| BIRD | ✅ Yes |
| OpenBGPD | ✅ Yes |
| FRR | ✅ Yes |
| ArcOS | ❌ No |
| GoBGP | ❌ No |
| ExaBGP | ❌ No |

> 📝 **Practical note:** if your platform already supports RFC 9234, configuring Roles is a relatively low-effort, high-value change — but expect to need a **maintenance window**, since applying a Role to an existing session typically requires a BGP session reset to take effect.

---

## Quick Comparison — OTC vs Other Route-Leak Defenses

| Mechanism | What It Protects Against | Enforcement |
|---|---|---|
| Manual prefix-lists / route-maps | Leaks, if configured correctly on both sides | Manual, error-prone, no cross-check |
| AS-PATH filtering | Some leak patterns (matching known bad AS_PATHs) | Manual, reactive |
| **BGP Roles + OTC (RFC 9234)** | Leaks violating valley-free routing, automatically | **Automatic**, enforced in-protocol via session negotiation + attribute marking |
| RPKI / ROV | Prefix hijacking (wrong origin AS) | Automatic, but solves a *different* problem (origin validation, not path-direction leaks) |

> 💡 **Bottom line:** RPKI validates *who's allowed to originate a prefix*; BGP Roles + OTC validate *which direction a route is allowed to keep traveling*. They solve complementary problems, and per Cloudflare's ASPA-related research, Roles are also what tells a router which path-validation algorithm to run — so the two mechanisms are increasingly meant to be configured together on routers that support both.