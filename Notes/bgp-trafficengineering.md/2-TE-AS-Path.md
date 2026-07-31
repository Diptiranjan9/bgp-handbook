## BGP Traffic Engineering with AS_PATH (Lab)

> 💡 **TL;DR:** Two labs in one — **outbound** AS_PATH prepending (on the advertised route) forces the ISP to prefer entering via ios-ed1 for your prefix. **Inbound** AS_PATH prepending (`prepend last-as`, applied on receipt) forces your own router to consistently prefer ios-ed1 for reaching external prefixes — even when both upstream paths look identical otherwise.

---

### Topology 

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-sp-lab.png)

- **inet-ceos** = Arista cEOS, AS 65002, dual-homed to AS 65000 via two eBGP links (10.0.4.1 → ios-ed1, 10.0.4.5 → junos-ed2)
- **ios-ed1** = Cisco IOS, AS 65000
- **junos-ed2** = Juniper, AS 65000 — internally connected to ios-ed1 via iBGP (seen via `eth2` / `10.0.3.1` next-hop in Junos output)
- AS 65000 provides transit to **10.10.10.10/32** and **11.11.11.11/32**, both originated in **AS 65001**

> 📝 **Multi-vendor note:** Commands differ slightly by platform — `show ip bgp regexp` (Cisco), `show ip bgp regex` (Arista cEOS), `show route ... aspath-regex` (Junos). Same AS_PATH regex concept, different CLI syntax.

---

### Before Traffic Engineering

**inet-ceos** sees two equal-cost paths to AS 65001 prefixes, both via AS 65000, same LocPref (100), same Weight (0):

```log
inet-ceos#show ip bgp summary 
BGP summary information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Neighbor Status Codes: m - Under maintenance
  Neighbor V AS           MsgRcvd   MsgSent  InQ OutQ  Up/Down State   PfxRcd PfxAcc PfxAdv
  10.0.4.1 4 65000            110       113    0    0 00:21:42 Estab   2      2      1
  10.0.4.5 4 65000            197       214    0    0 01:26:16 Estab   2      2      1

inet-ceos#show ip bgp 
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Route status codes: s - suppressed contributor, * - valid, > - active, E - ECMP head, e - ECMP
                    S - Stale, c - Contributing to ECMP, b - backup, L - labeled-unicast, q - Pending FIB install
                    % - Pending best path selection
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI Origin Validation codes: V - valid, I - invalid, U - unknown
AS Path Attributes: Or-ID - Originator ID, C-LST - Cluster List, LL Nexthop - Link Local Nexthop

          Network                Next Hop              Metric  AIGP       LocPref Weight  Path
 * >      10.10.10.10/32         10.0.4.1              0       -          100     0       65000 65001 i
 *        10.10.10.10/32         10.0.4.5              0       -          100     0       65000 65001 i
 * >      11.11.11.11/32         10.0.4.1              0       -          100     0       65000 65001 i
 *        11.11.11.11/32         10.0.4.5              0       -          100     0       65000 65001 i
 * >      172.16.1.0/24          -                     -       -          -       0       i
```

**ios-ed1 op:-**

```log
ios-ed1#show ip bgp regexp ^65002$
BGP table version is 24, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *bi  172.16.1.0/24    10.0.1.4                      120      0 65002 i
 *>                    10.0.4.2                      120      0 65002 i
```
**junos-ed2 op:-**

```log
root@junos-ed2> show route protocol bgp aspath-regex ^65002$ 

inet.0: 27 destinations, 30 routes (27 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

172.16.1.0/24      *[BGP/170] 01:04:40, localpref 120
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.4.6 via eth4
                    [BGP/170] 00:23:51, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)
```

**ios-ed1 / junos-ed2** both learn `172.16.1.0/24` from inet-ceos with a flat AS_PATH `65002 i` — no preference forced yet.

> 📝 **Why this matters:** With identical AS_PATH, LocPref, and Weight on both sides, the tiebreak falls to low-priority steps (Router ID, neighbor IP) — unpredictable and not something you want to rely on for TE.

---

## 1. Outbound Policy — Influencing the ISP's Inbound Decision

**Goal:** Force AS 65000 (the ISP) to always enter inet-ceos via **ios-ed1** (10.0.4.1) when reaching `172.16.1.0/24`.

### Config (on inet-ceos)

inet-ceos cfg:-

```ceos
ip as-path access-list out-65000 permit ^$ any
!
route-map to-ebgp2 permit 1
   match as-path out-65000
   set as-path prepend 650002 repeat 2
   set community community-list wan1
!
router bgp 65002
   router-id 172.16.1.1
   neighbor 10.0.4.1 remote-as 65000
   neighbor 10.0.4.1 route-map to-ebgp out
   neighbor 10.0.4.1 send-community standard
   neighbor 10.0.4.5 remote-as 65000
   neighbor 10.0.4.5 route-map to-ebgp2 out
   neighbor 10.0.4.5 send-community standard
   !
   address-family ipv4
      neighbor 10.0.4.1 activate
      neighbor 10.0.4.5 activate
      network 172.16.1.0/24
```

- `^$` matches an **empty AS_PATH** — i.e., only the locally originated prefix (`172.16.1.0/24`).
- The route-map applied **outbound to 10.0.4.5 only** prepends the AS_PATH twice, so that link's advertised path looks longer than the one sent to 10.0.4.1.

### Verification

**inet-ceos op:-**

```log
inet-ceos#show ip bgp summary 
BGP summary information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Neighbor Status Codes: m - Under maintenance
  Neighbor V AS           MsgRcvd   MsgSent  InQ OutQ  Up/Down State   PfxRcd PfxAcc PfxAdv
  10.0.4.1 4 65000            179       185    0    0 01:08:20 Estab   2      2      1
  10.0.4.5 4 65000            307       340    0    0 02:12:54 Estab   2      2      1


inet-ceos#show ip bgp regex ^$
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Route status codes: s - suppressed contributor, * - valid, > - active, E - ECMP head, e - ECMP
                    S - Stale, c - Contributing to ECMP, b - backup, L - labeled-unicast, q - Pending FIB install
                    % - Pending best path selection
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI Origin Validation codes: V - valid, I - invalid, U - unknown
AS Path Attributes: Or-ID - Originator ID, C-LST - Cluster List, LL Nexthop - Link Local Nexthop

          Network                Next Hop              Metric  AIGP       LocPref Weight  Path
 * >      172.16.1.0/24          -                     -       -          -       0       i

inet-ceos#show ip bgp neighbors 10.0.4.1 advertised-routes detail 
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Update wait-install is disabled
BGP routing table entry for 172.16.1.0/24
 Paths: 1 available
  65002
    10.0.4.2 from - (172.16.1.1)
      Origin IGP, metric -, localpref -, IGP metric -, weight -, tag 0
      Received 02:13:25 ago, valid, local, best, redistributed (Connected)
      Community: 65002:120
      Rx SAFI: Unicast


inet-ceos#show ip bgp neighbors 10.0.4.5 advertised-routes detail
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Update wait-install is disabled
BGP routing table entry for 172.16.1.0/24
 Paths: 1 available
  65002 650002 650002
    10.0.4.6 from - (172.16.1.1)
      Origin IGP, metric -, localpref -, IGP metric -, weight -, tag 0
      Received 02:13:32 ago, valid, local, best, redistributed (Connected)
      Community: 65002:120
      Rx SAFI: Unicast
```

**ios-ed1 op:-**

```log
ios-ed1#show ip bgp regexp ^65002.*
BGP table version is 25, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   172.16.1.0/24    10.0.4.2                      120      0 65002 i
```

**junos-ed2 op:-**

```log
root@junos-ed2> show route protocol bgp aspath-regex "^65002 .*"    

inet.0: 27 destinations, 31 routes (27 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

172.16.1.0/24      *[BGP/170] 01:09:59, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2
                    [BGP/170] 00:29:31, MED 0, localpref 120, from 10.0.1.2
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2
                    [BGP/170] 00:19:50, localpref 120
                      AS path: 65002 650002 650002 I, validation-state: unverified
                    >  to 10.0.4.6 via eth4

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)
```

> ⚠️ **Key insight:** junos-ed2 has a **direct eBGP link** to inet-ceos, but still prefers the **indirect, iBGP-learned path via ios-ed1** — because AS_PATH length is compared before "prefer eBGP over iBGP" (step 7 comes after AS_PATH at step 4). Prepending on just one link successfully steers the *entire AS's* entry point, not just that one router.

✅ **Result:** Both ISP edge routers now consistently select ios-ed1 as the path into inet-ceos.

---

## 2. Inbound Policy — Forcing Your Own Router's Path Selection

**Goal:** Make inet-ceos always prefer **ios-ed1** (10.0.4.1) when reaching AS 65001's prefixes, regardless of how AS 65000 advertises them.

### Config (on inet-ceos)

```ceos
ip as-path access-list in-65000 permit ^65000.* any
!
route-map from-65000 permit 1
   match as-path in-65000
   set as-path prepend last-as 2
!
router bgp 65002
   router-id 172.16.1.1
   neighbor 10.0.4.1 remote-as 65000
   neighbor 10.0.4.1 route-map to-ebgp out
   neighbor 10.0.4.1 send-community standard
   neighbor 10.0.4.5 remote-as 65000
   neighbor 10.0.4.5 route-map from-65000 in
   neighbor 10.0.4.5 route-map to-ebgp2 out
   neighbor 10.0.4.5 send-community standard
   !
   address-family ipv4
      neighbor 10.0.4.1 activate
      neighbor 10.0.4.5 activate
      network 172.16.1.0/24
```

- `^65000.*` matches any path starting with AS 65000 — i.e., every route learned from this AS.
- `prepend last-as 2` inserts **2 extra copies of the last AS in the path** (65000, the sending peer) — applied **inbound** on the 10.0.4.5 session only, as the route is received and installed into the local BGP table.

### Verification

**inet-ceos op:-**

```log
inet-ceos#sh ip bgp regex ^65000.*
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Route status codes: s - suppressed contributor, * - valid, > - active, E - ECMP head, e - ECMP
                    S - Stale, c - Contributing to ECMP, b - backup, L - labeled-unicast, q - Pending FIB install
                    % - Pending best path selection
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI Origin Validation codes: V - valid, I - invalid, U - unknown
AS Path Attributes: Or-ID - Originator ID, C-LST - Cluster List, LL Nexthop - Link Local Nexthop

          Network                Next Hop              Metric  AIGP       LocPref Weight  Path
 * >      10.10.10.10/32         10.0.4.1              0       -          100     0       65000 65001 i
 *        10.10.10.10/32         10.0.4.5              0       -          100     0       65000 65000 65000 65001 i
 * >      11.11.11.11/32         10.0.4.1              0       -          100     0       65000 65001 i
 *        11.11.11.11/32         10.0.4.5              0       -          100     0       65000 65000 65000 65001 i


inet-ceos#show ip bgp 10.10.10.10
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
BGP routing table entry for 10.10.10.10/32
 Paths: 2 available
  65000 65001
    10.0.4.1 from 10.0.4.1 (10.0.1.3)
      Origin IGP, metric 0, localpref 100, IGP metric 0, weight 0, tag 0
      Received 01:25:04 ago, valid, external, best
      Community: 65001:120 65001:1001
      Rx path id: 0x0
      Rx SAFI: Unicast
  65000 65000 65000 65001
    10.0.4.5 from 10.0.4.5 (10.0.1.4)
      Origin IGP, metric 0, localpref 100, IGP metric 0, weight 0, tag 0
      Received 02:30:40 ago, valid, external
      Community: 65001:120 65001:1002
      Rx SAFI: Unicast


inet-ceos#show ip bgp 11.11.11.11
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
BGP routing table entry for 11.11.11.11/32
 Paths: 2 available
  65000 65001
    10.0.4.1 from 10.0.4.1 (10.0.1.3)
      Origin IGP, metric 0, localpref 100, IGP metric 0, weight 0, tag 0
      Received 01:25:18 ago, valid, external, best
      Community: 65001:1001
      Rx path id: 0x0
      Rx SAFI: Unicast
  65000 65000 65000 65001
    10.0.4.5 from 10.0.4.5 (10.0.1.4)
      Origin IGP, metric 0, localpref 100, IGP metric 0, weight 0, tag 0
      Received 02:30:54 ago, valid, external
      Community: 65001:1002
      Rx SAFI: Unicast


inet-ceos#show ip bgp neighbors 10.0.4.1 received-routes detail
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
BGP routing table entry for 10.10.10.10/32
 Paths: 1 available
  65000 65001
    10.0.4.1 from 10.0.4.1 (10.0.1.3)
      Origin IGP, metric -, localpref -, IGP metric 0, weight -, tag 0
      Received 01:23:58 ago, valid, external, best
      Community: 65001:120 65001:1001
      Rx path id: 0x0
      Rx SAFI: Unicast
BGP routing table entry for 11.11.11.11/32
 Paths: 1 available
  65000 65001
    10.0.4.1 from 10.0.4.1 (10.0.1.3)
      Origin IGP, metric -, localpref -, IGP metric 0, weight -, tag 0
      Received 01:23:58 ago, valid, external, best
      Community: 65001:1001
      Rx path id: 0x0
      Rx SAFI: Unicast


inet-ceos#show ip bgp neighbors 10.0.4.5 received-routes detail
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
BGP routing table entry for 10.10.10.10/32
 Paths: 1 available
  65000 65001
    10.0.4.5 from 10.0.4.5 (10.0.1.4)
      Origin IGP, metric -, localpref -, IGP metric 0, weight -, tag 0
      Received 02:29:41 ago, valid, external
      Community: 65001:120 65001:1002
      Rx SAFI: Unicast
BGP routing table entry for 11.11.11.11/32
 Paths: 1 available
  65000 65001
    10.0.4.5 from 10.0.4.5 (10.0.1.4)
      Origin IGP, metric -, localpref -, IGP metric 0, weight -, tag 0
      Received 02:29:41 ago, valid, external
      Community: 65001:1002
      Rx SAFI: Unicast
```

✅ **Result:** With AS_PATH artificially lengthened only on the 10.0.4.5 path, inet-ceos deterministically picks ios-ed1 as best for both prefixes — confirmed by `show ip bgp <prefix>` marking the 10.0.4.1 path as `best`.

> 📝 **Why `prepend last-as` here, not a hardcoded ASN:** Since both paths originate from the same upstream AS (65000), prepending `last-as` (rather than a fixed number) automatically inserts that neighbor's own AS — a portable technique that doesn't need updating if the upstream ASN changes.

> ⚠️ **Gotcha — this differs from typical "inbound policy":** Normally, inbound TE means influencing what *you* prefer using LOCAL_PREF (attribute you control locally, never sent onward). Here, AS_PATH prepending is applied **inbound but modifies a propagable attribute** — if inet-ceos ever re-advertises these prefixes onward (e.g., in a transit scenario), the artificially prepended AS_PATH would go with it. In this lab that's fine since these are external routes not being transited further, but it's a meaningful distinction from LOCAL_PREF-based inbound policy.

---

### Outbound vs Inbound AS_PATH TE — Summary

| | Outbound Prepending | Inbound Prepending (`last-as`) |
|---|---|---|
| Applied on | Routes you **advertise** | Routes you **receive** |
| Influences | **Neighbor AS's** entry choice into you | **Your own router's** exit choice toward a prefix |
| Guarantee | No — neighbor's local policy can override | Yes — deterministically controls your own best-path outcome |
| Used here for | Steering ISP to enter via ios-ed1 | Steering inet-ceos to exit via ios-ed1 |