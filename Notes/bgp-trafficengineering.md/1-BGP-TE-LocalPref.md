## Traffic Engineering with LOCAL_PREF

> 💡 **TL;DR:** LOCAL_PREF controls **outbound** traffic — it tells routers *within your own AS* which exit point to prefer when multiple paths to the same external prefix exist. Higher LOCAL_PREF wins, and it only applies to iBGP (never sent to eBGP peers).

---

### Why Use LOCAL_PREF for Traffic Engineering?

- Used to influence **outbound traffic** — i.e., which exit path *your own AS* uses to reach an external prefix, when you have multiple eBGP connections (e.g., dual ISP, dual-homed sites).
- Since LOCAL_PREF is step 2 in the BGP Best Path algorithm (right after WEIGHT), it overrides AS_PATH length, MED, and other lower-priority attributes — a strong lever for TE.
- Propagates via iBGP to all routers in the AS, so a decision made at the edge is consistently honored network-wide.

---

### Lab Topology

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-sp-lab.png)

### Configuration

```ceos
route-map from-ebgp permit 1
   set local-preference 120
```

```ceos
router bgp 65002
   router-id 172.16.1.1
   neighbor 10.0.4.1 remote-as 65000
   neighbor 10.0.4.1 route-map from-ebgp in
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

### Verification

```log
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
 * >      10.10.10.10/32         10.0.4.1              0       -          120     0       65000 65001 i
 *        10.10.10.10/32         10.0.4.5              0       -          100     0       65000 65001 i
 * >      11.11.11.11/32         10.0.4.1              0       -          120     0       65000 65001 i
 *        11.11.11.11/32         10.0.4.5              0       -          100     0       65000 65001 i
 * >      172.16.1.0/24          -                     -       -          -       0       i
```

```log
inet-ceos#show ip bgp 10.10.10.10
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
BGP routing table entry for 10.10.10.10/32
 Paths: 2 available
  65000 65001
    10.0.4.1 from 10.0.4.1 (10.0.1.3)
      Origin IGP, metric 0, localpref 120, IGP metric 0, weight 0, tag 0
      Received 00:33:39 ago, valid, external, best
      Community: 65001:120 65001:1001
      Rx path id: 0x0
      Rx SAFI: Unicast
  65000 65001
    10.0.4.5 from 10.0.4.5 (10.0.1.4)
      Origin IGP, metric 0, localpref 100, IGP metric 0, weight 0, tag 0
      Received 00:37:49 ago, valid, external
      Community: 65001:120 65001:1002
      Rx SAFI: Unicast
```