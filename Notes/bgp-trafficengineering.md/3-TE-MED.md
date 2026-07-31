## Traffic Engineering with MED

> 💡 **TL;DR:** MED influences **inbound** traffic too — but unlike AS_PATH prepending, it's a numeric "suggestion" sent to a neighboring AS about which of *your multiple entry points* they should use, when they have more than one link into you. Lower MED wins, it's compared only between paths from the **same neighboring AS** by default, and the neighbor can ignore it entirely.

---

### Why Use MED for Traffic Engineering?

- Used when you have **multiple eBGP links to the same neighboring AS** (not different ASes) and want to tell them which link to prefer for inbound traffic to a given prefix.
- MED is compared **only between paths received from the same AS** by default — unlike AS_PATH prepending, which any AS along the path will factor in.
- Sits at **Step 6** in Best Path — after WEIGHT, LOCAL_PREF, locally-originated, AS_PATH length, and ORIGIN type. So it only takes effect if all of those are already tied.
- **Lower MED = more preferred** (opposite of LOCAL_PREF, where higher wins).

---

### Lab Topology

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-sp-lab.png)

---

### Before Traffic Engineering

Neither outbound route-map sets a MED — `metric` shows as `-` (unset) on both advertised paths:

**inet-ceos op:-**

```log
inet-ceos#show ip bgp summary 
BGP summary information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Neighbor Status Codes: m - Under maintenance
  Neighbor V AS           MsgRcvd   MsgSent  InQ OutQ  Up/Down State   PfxRcd PfxAcc PfxAdv
  10.0.4.1 4 65000            292       303    0    0 02:42:42 Estab   2      2      1
  10.0.4.5 4 65000            519       568    0    0 03:47:16 Estab   2      2      1


inet-ceos#show ip bgp neighbors 10.0.4.1 advertised-routes detail 
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Update wait-install is disabled
BGP routing table entry for 172.16.1.0/24
 Paths: 1 available
  65002
    10.0.4.2 from - (172.16.1.1)
      Origin IGP, metric -, localpref -, IGP metric -, weight -, tag 0
      Received 03:48:44 ago, valid, local, best, redistributed (Connected)
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
      Received 03:48:54 ago, valid, local, best, redistributed (Connected)
      Community: 65002:120
      Rx SAFI: Unicast
```

**ios-ed1 op:-**

```log
ios-ed1#show ip bgp regexp ^65002.*
BGP table version is 35, local router ID is 10.0.1.3
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

**junos-ed1 op:-**

```log
root@junos-ed2> show route protocol bgp aspath-regex "^65002 .*"    

inet.0: 27 destinations, 30 routes (27 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

172.16.1.0/24      *[BGP/170] 00:03:02, localpref 120
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.4.6 via eth4
                    [BGP/170] 00:03:06, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)
```

---

### Configuration

```ceos
route-map to-ebgp permit 1
   match ip address prefix-list lan
   set metric 1
route-map to-ebgp2 permit 1
   match ip address prefix-list lan
   set metric 2
!
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

---

### Verification / Output

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
      Origin IGP, metric 1, localpref -, IGP metric -, weight -, tag 0
      Received 03:53:43 ago, valid, local, best, redistributed (Connected)
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
      Origin IGP, metric 2, localpref -, IGP metric -, weight -, tag 0
      Received 03:53:49 ago, valid, local, best, redistributed (Connected)
      Community: 65002:120
      Rx SAFI: Unicast
```

**ios-ed1 op:-**

```log
ios-ed1#show ip bgp regexp ^65002.*
BGP table version is 42, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>   172.16.1.0/24    10.0.4.2                 1    120      0 65002 i

ios-ed1#show ip bgp 172.16.1.0/24
BGP routing table entry for 172.16.1.0/24, version 42
Paths: (1 available, best #1, table default)
  Additional-path-install
  Advertised to update-groups:
     5          6         
  Refresh Epoch 9
  65002
    10.0.4.2 from 10.0.4.2 (172.16.1.1)
      Origin IGP, metric 1, localpref 120, valid, external, best
      Community: 65002:120 , recursive-via-connected
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 12 2026 07:50:27 UTC
```

**junos-ed2 op:-**

```log
root@junos-ed2> show route protocol bgp aspath-regex "^65002 .*"    

inet.0: 27 destinations, 31 routes (27 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

172.16.1.0/24      *[BGP/170] 00:03:02, MED 1, localpref 120, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2
                    [BGP/170] 00:03:02, MED 1, localpref 120, from 10.0.1.2
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2
                    [BGP/170] 00:03:02, MED 2, localpref 120
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.4.6 via eth4

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)
```

---

### Key Takeaways

✅ **Result:** Every router in AS 65000 — including both edge routers and both Route Reflectors — converges on the path **originated at ios-ed1 (MED 1)** as best, exactly as intended.

> ⚠️ **Key insight — MED beats "prefer eBGP over iBGP":** At **junos-ed2**, the directly connected eBGP path (MED 2) loses to the **iBGP-learned** path via ios-ed1 (MED 1). This confirms MED comparison (Step 6) happens **before** the eBGP-over-iBGP preference (Step 7) — a lower MED can override having a "closer," directly connected eBGP session.


> ⚠️ **Gotcha:** MED is only compared between paths from the **same AS** unless `bgp always-compare-med` is configured — if your two links are to *different* neighboring ASes rather than the same one, MED won't naturally decide anything; use AS_PATH prepending or LOCAL_PREF instead.