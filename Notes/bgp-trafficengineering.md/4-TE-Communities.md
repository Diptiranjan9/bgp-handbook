## BGP Communities & Traffic Engineering

> 💡 **TL;DR:** A BGP Community is an optional transitive attribute that tags a prefix with a 32-bit label, letting you attach arbitrary "meaning" to routes (e.g., "this is a backup path," "don't announce to peer X") without needing complex AS-PATH filters or per-neighbor route-maps. ISPs publish their own community definitions (there's no universal standard beyond a handful of well-known values), and customers set these communities to control how their upstream treats their prefixes — this is the foundation of most real-world BGP traffic engineering.

Related: [[BGP Attributes]] · [[Traffic Engineering with AS_PATH]] · [[Traffic Engineering with MED]] · [[Traffic Engineering with LOCAL_PREF]]

Reference: [NSRC/APRICOT — Using BGP Communities](https://nsrc.org/workshops/2017/apricot2017/bgp/bgp/preso/09-BGP-Communities.pdf)

---

### What is a BGP Community?

- An **optional transitive** path attribute (Type Code 8) attached to a prefix.
- Format: a **32-bit value**, conventionally written and configured as **`ASN:VALUE`** (e.g., `100:80`) — the first 16 bits are usually the AS number, the last 16 bits are a locally-defined meaning chosen by that AS.
- A single prefix can carry **multiple communities** at once.
- The community attribute itself doesn't *do* anything automatically — it's used as a way to help scale BGP policies and multihoming setups because a router at the receiving end matches on the community value and then takes an explicit action (set local-pref, prepend, filter, etc.) via a route-map.

> 📝 **Why it matters:** Without communities, controlling policy on 50 different neighbors means 50 different route-maps/prefix-lists. With communities, a customer tags a prefix once, and every downstream router just matches that tag — dramatically less config to maintain.

---

### Types of BGP Communities

| Type | Size | Format | Use Case |
|---|---|---|---|
| **Standard Community** | 32-bit | `ASN:VALUE` (16-bit : 16-bit) | Most common — local pref, prepend, filtering |
| **Extended Community** | 64-bit | Type + Value fields | MPLS VPNs (Route Target, Route Origin), more structured use cases |
| **Large Community** (RFC 8092) | 96-bit | `ASN:function:parameter` (three 32-bit fields) | Needed once 4-byte ASNs became common — standard communities can't cleanly embed a 4-byte ASN in a 16-bit field |

> ⚠️ **Gotcha:** Standard communities were designed when ASNs were 2-byte. Once 4-byte ASNs (RFC 6793) became common, ISPs with large ASNs (e.g., 400000+) couldn't fit their own ASN into a standard community's 16-bit field — this is exactly why **Large Communities** were introduced.

---

### Well-Known Communities

A small set of communities are standardized by IANA and understood universally by all BGP implementations — these are documented at www.iana.org/assignments/bgp-well-known-communities, and no other community values carry universal meaning.

| Well-Known Community | Effect |
|---|---|
| `NO_EXPORT` | Don't advertise this route outside the local AS (or confederation boundary) |
| `NO_ADVERTISE` | Don't advertise this route to any BGP peer at all — keep it purely local |
| `NO_EXPORT_SUBCONFED` | Don't advertise outside the local AS, and don't advertise to other members of the confederation either |
| `NO_PEER` (RFC 3765) | Don't advertise to bilateral peers — advertise only to customers/transit relationships |

> 📝 **Important distinction:** Outside of these well-known values, there are no standardized "recommended" community meanings across ISPs — every ISP defines its own custom community numbering, which is why the workshop material spends most of its time showing example ISP community tables (Verizon, Telia, Level3, BT) rather than a single universal scheme.

---

### Transitive vs Non-Transitive

- The **standard BGP Community attribute itself is Optional Transitive** — meaning if AS B receives a community-tagged prefix from AS A and doesn't understand or strip it, the community is passed along to AS C, D, etc. as the route propagates.
- This transitive nature is exactly what makes RFC 1998-style customer-to-upstream TE work: a customer sets a community once, and it survives being carried across the upstream's own internal and external announcements — until something (usually a route-map) strips it.
- Most ISPs **strip customer-facing communities before re-advertising further upstream** (to avoid leaking internal signaling to the wider internet) — this is a deliberate configuration choice, not a protocol requirement.

> ⚠️ **Gotcha:** "Transitive" doesn't mean "unstoppable." An ISP can (and usually does) explicitly strip or filter communities at AS boundaries using route-maps — transitivity just means the *protocol* won't silently drop it on its own the way it would for an Optional Non-Transitive attribute like MED.

---

### RFC 1998 — The Original TE-via-Community Pattern

RFC 1998 is an informational RFC describing how to implement load-sharing and backup across multiple inter-AS links, using BGP communities to influence local preference within the upstream's network — giving the customer direct control without needing to contact the upstream's support team.

**Standard RFC 1998 community meanings** (as originally proposed, `ASx` = upstream's own AS number):

| Community | Meaning |
|---|---|
| `ASx:100` | Set Local Preference 100 — make this the preferred path |
| `ASx:90` | Set Local Preference 90 — backup if dual-homed to same AS |
| `ASx:80` | Set Local Preference 80 — main link is to another ISP, same AS_PATH length |
| `ASx:70` | Set Local Preference 70 — main link is to another ISP |

**Customer side (announcing with a community):**
```cisco
router bgp 130
 neighbor x.x.x.x remote-as 100
 neighbor x.x.x.x route-map as100-out out
 neighbor x.x.x.x send-community
!
ip as-path access-list 20 permit ^$
!
route-map as100-out permit 10
 match as-path 20
 set community 100:70
```

**ISP side (matching and acting on the community):**
```cisco
router bgp 100
 neighbor y.y.y.y remote-as 130
 neighbor y.y.y.y route-map customer-policy-in in
!
ip community-list 7 permit 100:70
ip community-list 8 permit 100:80
ip community-list 9 permit 100:90
!
route-map customer-policy-in permit 10
 match community 7
 set local-preference 70
route-map customer-policy-in permit 20
 match community 8
 set local-preference 80
route-map customer-policy-in permit 30
 match community 9
 set local-preference 90
route-map customer-policy-in permit 40
 set local-preference 100
```

> 📝 **Note:** `neighbor ... send-community` is required on **both sides** — Cisco/IOS does not send community attributes by default; forgetting this is one of the most common reasons community-based policy silently fails to work.

---

### Typical Modern ISP Community Patterns

Since RFC 1998, most large ISPs extended the idea well beyond just local preference. Common patterns seen across real ISPs (Verizon, Telia, Level3, BT, etc.):

| Community Pattern | Typical Meaning |
|---|---|
| `X:80` / `X:120` | Set Local Preference 80 (backup) / 120 (primary) |
| `X:1` / `X:2` / `X:3` | Prepend AS X once / twice / thrice when announced to X's upstreams |
| `X:666` or `X:9999` | Blackhole (discard) traffic — commonly used for DoS mitigation |
| `X:5000` | Don't announce to any BGP neighbor at all |
| `X:5MM0` | Don't announce to a specific neighbor `MM` |
| `X:5MMN` | Prepend `N` times specifically toward neighbor `MM` |

> ⚠️ **Gotcha — Blackhole communities:** A "blackhole" community typically works by setting the route's next-hop to a null/discard address (e.g., 192.0.2.1 routed to null0) rather than literally deleting the route — this lets an ISP's customers signal "drop traffic to this specific /32 under attack" without a phone call, while keeping the rest of their announced space intact.

---

### Communities for iBGP / Backbone Scaling

Beyond customer-facing TE, ISPs also use communities **internally**, tagging prefixes as they enter the network so that Route Reflectors and edge routers can filter/distribute them purely by matching community — no AS-PATH filters or prefix-lists needed internally.

Common internal tagging categories:

| Purpose | Example |
|---|---|
| Identify own aggregate blocks | `100:1000` |
| Identify aggregate sub-prefixes | `100:1001` |
| Identify static/PI customer space | `100:1005` |
| Identify which service tier a customer bought (transit / IXP / BGP-only) | `100:2000`, `100:2100`, `100:2200` |
| Identify routes learned from an IXP | `100:3000` |

> 📝 **Why this scales better:** Once every prefix is tagged on ingress, all downstream policy (what a Route Reflector sends to its clients, what gets announced to upstreams vs IXP peers) becomes a single `match community` line — instead of maintaining separate prefix-lists or AS-PATH filters per neighbor as the network grows.

---

### Comparison — Where Communities Fit Among TE Tools

| Technique | Direction | Mechanism | Guarantee | Scales to many neighbors? |
|---|---|---|---|---|
| LOCAL_PREF | Outbound (your exit) | Attribute set locally | Yes | N/A (internal only) |
| AS_PATH Prepend | Inbound (neighbor's entry) | Lengthen AS_PATH | No | Poorly — per-neighbor route-maps |
| MED | Inbound (neighbor's entry, same AS) | Numeric metric | No | Poorly — per-neighbor route-maps |
| **BGP Community** | Both — customer signals, ISP acts | Tag + remote route-map action | Depends on ISP's policy | **Yes** — one tag drives many downstream decisions |

> 💡 **Key takeaway:** Communities don't replace LOCAL_PREF/MED/AS_PATH — they're the **delivery mechanism** that lets a customer or downstream router remotely trigger those exact same underlying mechanisms, at scale, without needing bespoke config per session.

---

### Lab Topology

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-sp-lab.png)

---

### Before Traffic Engineering

**inet-ceos op:-**

```log
inet-ceos#show ip bgp neighbors 10.0.4.1 advertised-routes detail 
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Update wait-install is disabled
BGP routing table entry for 172.16.1.0/24
 Paths: 1 available
  65002
    10.0.4.2 from - (172.16.1.1)
      Origin IGP, metric -, localpref -, IGP metric -, weight -, tag 0
      Received 04:02:45 ago, valid, local, best, redistributed (Connected)
      Rx SAFI: Unicast


inet-ceos#show ip bgp neighbors 10.0.4.5 advertised-routes detail
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Update wait-install is disabled
BGP routing table entry for 172.16.1.0/24
 Paths: 1 available
  65002
    10.0.4.6 from - (172.16.1.1)
      Origin IGP, metric -, localpref -, IGP metric -, weight -, tag 0
      Received 04:02:53 ago, valid, local, best, redistributed (Connected)
      Rx SAFI: Unicast
```

**ios-ed1 op:-**

```log
ios-ed1#show ip bgp regexp ^65002$
BGP table version is 50, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *bi  172.16.1.0/24    10.0.1.4                      100      0 65002 i
 *>                    10.0.4.2                               0 65002 i

ios-ed1#show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 50
Paths: (2 available, best #2, table default)
  Additional-path-install
  Advertised to update-groups:
     5          6         
  Refresh Epoch 1
  65002
    10.0.1.4 (metric 1) from 10.0.1.2 (10.0.1.2)
      Origin IGP, localpref 100, valid, internal, backup/repair
      Originator: 10.0.1.4, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 12 2026 08:00:50 UTC
  Refresh Epoch 9
  65002
    10.0.4.2 from 10.0.4.2 (172.16.1.1)
      Origin IGP, localpref 100, valid, external, best , recursive-via-connected
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 12 2026 08:00:45 UTC
```

**junos-ed2 op:-**

```log
root@junos-ed2> show route protocol bgp aspath-regex ^65002 

inet.0: 27 destinations, 30 routes (27 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

172.16.1.0/24      *[BGP/170] 00:01:12, localpref 100
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.4.6 via eth4
                    [BGP/170] 00:01:12, MED 0, localpref 100, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)


root@junos-ed2> show route protocol bgp 172.16.1.0/24 detail   

inet.0: 27 destinations, 30 routes (27 active, 0 holddown, 0 hidden)
172.16.1.0/24 (2 entries, 1 announced)
        *BGP    Preference: 170/-101
                Next hop type: Router, Next hop index: 0
                Address: 0xaaab06cdb9bc
                Next-hop reference count: 2, Next-hop session id: 0
                Kernel Table Id: 0
                Source: 10.0.4.6
                Next hop: 10.0.4.6 via eth4, selected
                Session Id: 0
                State: <Active Ext>
                Peer AS: 65002
                Age: 4:16 
                Validation State: unverified 
                Task: BGP_65002_65000.10.0.4.6
                Announcement bits (4): 1-KRT MFS 2-KRT 5-BGP_RT_Background 6-Resolve tree 1 
                AS path: 65002 I 
                Accepted
                Localpref: 100
                Router ID: 172.16.1.1
                Thread: junos-main 
         BGP    Preference: 170/-101
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaab0dd11ddc
                Next-hop reference count: 1
                Kernel Table Id: 0
                Source: 10.0.1.1
                Next hop type: Router, Next hop index: 0
                Next hop: 10.0.3.1 via eth2, selected
                Session Id: 0
                Protocol next hop: 10.0.1.3
                Indirect next hop: 0xaaab06dbb410 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext Changed>
                Inactive reason: Not Best in its group - Interior > Exterior > Exterior via Interior
                Peer AS: 65000
                Age: 4:16       Metric: 0       Metric2: 2 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.1
                AS path: 65002 I  (Originator)
                Cluster list:  10.0.1.1
                Originator ID: 10.0.1.3
                Accepted
                Localpref: 100
                Router ID: 10.0.1.1     
                Thread: junos-main 
```

---

### Configuration

**inet-ceos cfg:-**

```ceos
ip community-list wan1 permit 65002:120   <<< When ISP get this community value it will set local-pref 120 
ip community-list wan2 permit 65002:90    <<< When ISP get this community value it will set local-pref 90
!
route-map to-ebgp permit 1
   match ip address prefix-list lan
   set community community-list wan1
route-map to-ebgp2 permit 1
   match ip address prefix-list lan
   set community community-list wan2
!
router bgp 65002
   neighbor 10.0.4.1 route-map to-ebgp out
   neighbor 10.0.4.5 route-map to-ebgp2 out
```

**ios-ed1 cfg:-**

```cisco
ip bgp-community new-format
ip community-list standard ceos-65002-1 permit 65002:120
ip community-list standard ceos-65002-2 permit 65002:90
!
ip prefix-list ceos-65002 seq 5 permit 172.16.1.0/24
!
route-map ceos-65002 permit 4 
 match community ceos-65002-1
 set local-preference 120
route-map ceos-65002 permit 5 
 match community ceos-65002-2
 set local-preference 90
route-map ceos-65002 permit 6 
 match ip address prefix-list ceos-65002
!
router bgp 65000
address-family ipv4
 neighbor 10.0.4.2 activate
 neighbor 10.0.4.2 send-community both
 neighbor 10.0.4.2 route-map ceos-65002 in
end
```

**junos-ed2 cfg:-**

```sh
set policy-options community ceos-65002-1 members 65002:120
set policy-options community ceos-65002-2 members 65002:90 
set policy-options prefix-list ceos-65002 172.16.1.0/24
set policy-options policy-statement ceos-65002 term 1 from community ceos-65002-1
set policy-options policy-statement ceos-65002 term 1 then local-preference 120
set policy-options policy-statement ceos-65002 term 1 then accept
set policy-options policy-statement ceos-65002 term 2 from community ceos-65002-2
set policy-options policy-statement ceos-65002 term 2 then local-preference 90
set policy-options policy-statement ceos-65002 term 2 then accept
set policy-options policy-statement ceos-65002 term 3 from prefix-list ceos-65002
set policy-options policy-statement ceos-65002 term 3 then accept
set policy-options policy-statement ceos-65002 term 10 then reject
set protocols bgp group inet-ceos local-address 10.0.4.5
set protocols bgp group inet-ceos import ceos-65002
set protocols bgp group inet-ceos peer-as 65002
set protocols bgp group inet-ceos local-as 65000
set protocols bgp group inet-ceos neighbor 10.0.4.6
```

---

### Verification

**inet-ceos op:-**

```log
inet-ceos#show ip bgp neighbors 10.0.4.1 advertised-routes detail 
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Update wait-install is disabled
BGP routing table entry for 172.16.1.0/24
 Paths: 1 available
  65002
    10.0.4.2 from - (172.16.1.1)
      Origin IGP, metric -, localpref -, IGP metric -, weight -, tag 0
      Received 04:11:43 ago, valid, local, best, redistributed (Connected)
      Community: 65002:120
      Rx SAFI: Unicast

inet-ceos#show ip bgp neighbors 10.0.4.5 advertised-routes detail
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Update wait-install is disabled
BGP routing table entry for 172.16.1.0/24
 Paths: 1 available
  65002
    10.0.4.6 from - (172.16.1.1)
      Origin IGP, metric -, localpref -, IGP metric -, weight -, tag 0
      Received 04:11:59 ago, valid, local, best, redistributed (Connected)
      Community: 65002:90
      Rx SAFI: Unicast
```


**ios-ed1 op:-**

```log
ios-ed1#show ip bgp regexp ^65002.*
BGP table version is 52, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   172.16.1.0/24    10.0.4.2                      120      0 65002 i

ios-ed1#show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 52
Paths: (1 available, best #1, table default)
  Additional-path-install
  Advertised to update-groups:
     5          6         
  Refresh Epoch 9
  65002
    10.0.4.2 from 10.0.4.2 (172.16.1.1)
      Origin IGP, localpref 120, valid, external, best
      Community: 65002:120 , recursive-via-connected
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 12 2026 08:09:04 UTC
```

**junos-ed2 op:-**

```log
root@junos-ed2> show route protocol bgp aspath-regex ^65002.* 

inet.0: 27 destinations, 31 routes (27 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

172.16.1.0/24      *[BGP/170] 00:07:54, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2
                    [BGP/170] 00:07:54, MED 0, localpref 120, from 10.0.1.2
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2
                    [BGP/170] 00:07:48, localpref 90
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.4.6 via eth4

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)

root@junos-ed2> show route receive-protocol bgp 10.0.4.6 

inet.0: 27 destinations, 31 routes (27 active, 0 holddown, 0 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
  172.16.1.0/24           10.0.4.6                                65002 I

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)


root@junos-ed2> show route protocol bgp aspath-regex ^65002.* detail 

inet.0: 27 destinations, 31 routes (27 active, 0 holddown, 0 hidden)
172.16.1.0/24 (3 entries, 1 announced)
        *BGP    Preference: 170/-121
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaab0dd11ddc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.1
                Next hop type: Router, Next hop index: 0
                Next hop: 10.0.3.1 via eth2, selected
                Session Id: 0
                Protocol next hop: 10.0.1.3
                Indirect next hop: 0xaaab06dbb410 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <Active Int Ext>
                Peer AS: 65000
                Age: 8:46       Metric: 0       Metric2: 2 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.1
                Announcement bits (3): 1-KRT MFS 2-KRT 6-Resolve tree 1 
                AS path: 65002 I  (Originator)
                Cluster list:  10.0.1.1
                Originator ID: 10.0.1.3
                Communities: 65002:120
                Accepted
                Localpref: 120
                Router ID: 10.0.1.1
                Thread: junos-main 
         BGP    Preference: 170/-121
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaab0dd11ddc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.2
                Next hop type: Router, Next hop index: 0
                Next hop: 10.0.3.1 via eth2, selected
                Session Id: 0
                Protocol next hop: 10.0.1.3
                Indirect next hop: 0xaaab06dbb410 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext Changed>
                Inactive reason: Not Best in its group - Update source
                Peer AS: 65000
                Age: 8:46       Metric: 0       Metric2: 2 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.2
                AS path: 65002 I  (Originator)
                Cluster list:  10.0.1.2
                Originator ID: 10.0.1.3
                Communities: 65002:120
                Accepted
                Localpref: 120
                Router ID: 10.0.1.2
                Thread: junos-main 
         BGP    Preference: 170/-91
                Next hop type: Router, Next hop index: 0
                Address: 0xaaab06cdb9bc
                Next-hop reference count: 1, Next-hop session id: 0
                Kernel Table Id: 0
                Source: 10.0.4.6
                Next hop: 10.0.4.6 via eth4, selected
                Session Id: 0
                State: <Ext Changed>
                Inactive reason: Local Preference
                Peer AS: 65002
                Age: 8:40 
                Validation State: unverified 
                Task: BGP_65002_65000.10.0.4.6
                AS path: 65002 I 
                Communities: 65002:90
                Accepted
                Localpref: 90
                Router ID: 172.16.1.1
                Thread: junos-main 

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)
```