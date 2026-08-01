# BGP Security — Destination-Based RTBH

> 💡 **TL;DR:** RTBH (Remotely Triggered Black Hole filtering, RFC 5635) is a DoS mitigation technique used within a single AS. It leverages the BGP **NEXT_HOP** attribute (pointed at a discard/Null0 route) and optionally the **Community** attribute to remotely trigger edge routers to drop traffic — without needing to touch every router's config by hand. **Destination-Based RTBH** is the original implementation: it takes the *victim* offline by discarding all traffic destined to it, using either Next-Hop alteration or Community-based signaling from the customer.

Related: [[BGP Security — Source-Based RTBH]] · [[BGP Attributes]] · [[BGP Community]] · [[BGP Path Selection]]

Reference: [RFC 5635 — Remote Triggered Black Hole Filtering with BGP](https://datatracker.ietf.org/doc/html/rfc5635)

---

## Table of Contents

- [BGP Security — Destination-Based RTBH](#bgp-security--destination-based-rtbh)
  - [Table of Contents](#table-of-contents)
  - [RTBH Introduction](#rtbh-introduction)
    - [BGP NEXT-HOP Attribute](#bgp-next-hop-attribute)
    - [Discard Routes](#discard-routes)
    - [BGP Community Attribute](#bgp-community-attribute)
  - [Destination Based RTBH](#destination-based-rtbh)
    - [Network Diagram](#network-diagram)
    - [Next-Hop Attribute Based RTBH (Lab)](#next-hop-attribute-based-rtbh-lab)
      - [Before Config](#before-config)
      - [After Config](#after-config)
    - [Community Attribute Based RTBH (Lab)](#community-attribute-based-rtbh-lab)
      - [Before Config](#before-config-1)
      - [After Config and Community sent from bird3-1 peer](#after-config-and-community-sent-from-bird3-1-peer)
  - [References](#references)

---

## RTBH Introduction

- DoS mitigation technique.
- Applicable **within a single AS** — usually the provider's own network.
- Leverages two main BGP attributes:
  - **BGP Next-Hop attribute**
  - **BGP Community attribute** (optional)
- Two separate implementations:
  - **Destination Based RTBH** — takes the *victim* offline (drops all traffic to it).
  - **Source Based RTBH** — blocks the *attacker* (drops traffic sourced from it). See [[BGP Security — Source-Based RTBH]].

---

### BGP NEXT-HOP Attribute

- Typically an IPv4 or IPv6 address.
- Affects how the NLRI (prefix) gets installed in the FIB:
  - The next-hop is resolved via a **recursive routing lookup**.
  - Ultimately, an **exit interface** must be determined.

**Example — normal recursive next-hop resolution:**

```log
RR6#show ip route 100.100.100.0
Routing entry for 100.100.100.0/24
    Known via "bgp 1", distance 200, metric 0
    Tag 8, type internal
    Last update from 4.4.4.4 00:00:17 ago
    Routing Descriptor Blocks:
    * 4.4.4.4, from 4.4.4.4, 00:00:17 ago
        Route metric is 0, traffic share count is 1
    AS Hops 1
        Route tag 8
        MPLS label: none
!
RR6#show ip cef 100.100.100.0/24 det
100. 100.100.0/24, epoch 2, flags [rib only nolabel, rib defined all labels]
    recursive via 4.4.4.4
        nexthop 10.5.6.5 GigabitEthernet3 label 18-(local: 22)
```

> 📝 **Why this matters for RTBH:** Since a router must resolve the next-hop before it can forward traffic, RTBH exploits this by making that resolution point at a **discard route** instead of a real path — see below.

---

### Discard Routes

- A discard route is used to **drop traffic**.
  - Usually a static route.
  - All traffic that maps to this route in the FIB is dropped.
  - Also called a **Bit Bucket** or a **Null0 route**.
- For BGP NLRIs, this can be achieved two ways:
  - **Programmatically** (IOS-XR, Junos — a native `discard` next-hop type).
  - **Setting the NH to a Discard Route** (most common approach). RFC 5635 recommends using `192.0.2.1` (TEST-NET-1) as the conventional discard next-hop IP.

**Example — a route resolving to a discard/Null0 next-hop:**

```log
Routing entry for 100.100.100.0/24
    Known via "bgp 1", distance 200,
    metric o, type internal
    Last update from 192.0.0.1 00:00:13 ago
    Routing Descriptor Blocks:
    * 192.0.2.1, from 1.1.1.3, 00:00:13 ago
        Route metric is o, traffic share count is 1
        AS Hops 0
        MPLS label: none

R1#show ip cef 100.100.100.0/24
100. 100.100.0/24
    nexthop 192.0.2.1 Nullo
```

---

### BGP Community Attribute

- An **optional transitive** BGP attribute.
- Just a numerical value:
  - **Standard** (32 bits)
  - **Extended** (64 bits)
- Used to group NLRIs associated with a common policy, e.g.:
  - Set Local Preference to 500
  - Set Next Hop to discard
- **Well-Known Communities:**
  - `NO_EXPORT` (`65535:65281`) is the community applicable to RTBH — it can be advertised to iBGP peers but **not** to eBGP peers, keeping the RTBH trigger contained within the AS.

---

## Destination Based RTBH

- The **original** RTBH implementation.
- Filters/drops **all traffic to a particular destination** — typically the victim of the DoS attack(s).
- The trigger router can be:
  - The CE (Customer Edge)
  - A dedicated RTBH Trigger Router
- The customer uses **communities** to signal which prefix to black-hole.
- The trigger router has multiple options for propagating the black-hole to the rest of the AS:
  - **Communities**, or
  - **Next-Hop alteration**

### Network Diagram

![BGP SP Lab — RTBH](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-sp-lab-rtbh.png)

---

### Next-Hop Attribute Based RTBH (Lab)

- **Trigger Router Originated** — the RTBH trigger router itself originates the black-hole route.
- **Customer Signaled** — a customer network is the victim.

#### Before Config

**ios-rr1 op:-**

```log
ios-rr1#show ip bgp 10.10.10.10
BGP routing table entry for 10.10.10.10/32, version 2
Paths: (3 available, best #1, table default)
  Additional-path-install
  Advertised to update-groups:
     2          3          4          5         
  Refresh Epoch 1
  65001, (Received from a RR-client)
    10.0.1.5 (metric 2) from 10.0.1.5 (10.0.1.5)
      Origin IGP, metric 0, localpref 120, valid, internal, best
      Community: 65001:120 65001:1001
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 23 2026 02:46:12 UTC
  Refresh Epoch 1
  65001, (Received from a RR-client)
    10.0.1.6 (metric 2) from 10.0.1.6 (10.0.1.6)
      Origin IGP, localpref 120, valid, internal, backup/repair
      Community: 65001:120 65001:1002
      rx pathid: 0, tx pathid: 0
      Updated on Jul 23 2026 02:45:20 UTC
  Refresh Epoch 1
  65001
    10.0.1.6 (metric 2) from 10.0.1.2 (10.0.1.2)
      Origin IGP, localpref 120, valid, internal
      Community: 65001:120 65001:1002
      Originator: 10.0.1.6, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 23 2026 02:45:19 UTC

ios-rr1#show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "bgp 65000", distance 200, metric 0
  Tag 65001, type internal
  Last update from 10.0.1.5 00:01:14 ago
  Routing Descriptor Blocks:
  * 10.0.1.5, from 10.0.1.5, 00:01:14 ago
      opaque_ptr 0x7FFFDDE85660 
      Route metric is 0, traffic share count is 1
      AS Hops 1
      Route tag 65001
      MPLS label: none

ios-rr1#show ip cef 10.10.10.10
10.10.10.10/32
  nexthop 10.0.2.10 Ethernet0/2
```

**junos-rr2 op:-**

```log
root@junos-rr2> show route fib-expanded-nh 10.10.10.10 
root@junos-rr2> show route best 10.10.10.10
root@junos-rr2> show route protocol bgp 10.10.10.10    <<<< Three command op is same

inet.0: 31 destinations, 38 routes (31 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.10.10.10/32     *[BGP/170] 00:06:45, localpref 120, from 10.0.1.6
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.2.14 via eth2
                    [BGP/170] 00:05:42, MED 0, localpref 120, from 10.0.1.5
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.2.1 via eth1
                       to 10.0.2.14 via eth2
                    [BGP/170] 00:05:29, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.2.1 via eth1
                       to 10.0.2.14 via eth2
```

**rtbh op:-**

```log
rtbh# show ip bgp 10.10.10.10
BGP routing table entry for 10.10.10.10/32, version 1
Paths: (2 available, best #1, table default)
  Not advertised to any peer
  65001
    10.0.1.6 (metric 11) from 10.0.1.2 (10.0.1.6)
      Origin IGP, localpref 120, valid, internal, best (IGP Metric)
      Community: 65001:120 65001:1002
      Originator: 10.0.1.6, Cluster list: 10.0.1.2 
      Last update: Thu Jul 23 02:45:16 2026
  65001
    10.0.1.5 (metric 12) from 10.0.1.1 (10.0.1.5)
      Origin IGP, metric 0, localpref 120, valid, internal
      Community: 65001:120 65001:1001
      Originator: 10.0.1.5, Cluster list: 10.0.1.1 
      Last update: Thu Jul 23 02:46:25 2026


rtbh# show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "bgp", distance 200, metric 0, best
  Last update 00:13:59 ago
    10.0.1.6 (recursive), weight 1
  *   10.0.2.25, via eth2, weight 1
```

**inet-ceos op:-**

```log
inet-ceos#show ip bgp 10.10.10.10
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
BGP routing table entry for 10.10.10.10/32
 Paths: 2 available
  65000 65001
    10.0.4.1 from 10.0.4.1 (10.0.1.3)
      Origin IGP, metric 0, localpref 120, IGP metric 0, weight 0, tag 0
      Received 00:01:48 ago, valid, external, best
      Community: 65001:120 65001:1001
      Rx path id: 0x0
      Rx SAFI: Unicast
  65000 65001
    10.0.4.5 from 10.0.4.5 (10.0.1.4)
      Origin IGP, metric 0, localpref 100, IGP metric 0, weight 0, tag 0
      Received 00:20:20 ago, valid, external
      Community: 65001:120 65001:1002
      Rx SAFI: Unicast

inet-ceos#show ip route 10.10.10.10

VRF: default
Source Codes:
       C - connected, S - static, K - kernel,
       O - OSPF, O IA - OSPF inter area, O E1 - OSPF external type 1,
       O E2 - OSPF external type 2, O N1 - OSPF NSSA external type 1,
       O N2 - OSPF NSSA external type2, O3 - OSPFv3,
       O3 IA - OSPFv3 inter area, O3 E1 - OSPFv3 external type 1,
       O3 E2 - OSPFv3 external type 2,
       O3 N1 - OSPFv3 NSSA external type 1,
       O3 N2 - OSPFv3 NSSA external type2, B - Other BGP Routes,
       B I - iBGP, B E - eBGP, R - RIP, I L1 - IS-IS level 1,
       I L2 - IS-IS level 2, A B - BGP Aggregate,
       A O - OSPF Summary, NG - Nexthop Group Static Route,
       V - VXLAN Control Service, M - Martian,
       DH - DHCP client installed default route,
       DP - Dynamic Policy Route, L - VRF Leaked,
       G  - gRIBI, RC - Route Cache Route,
       CL - CBF Leaked Route

 B E      10.10.10.10/32 [200/0]
           via 10.0.4.1, Ethernet1
```

#### After Config

**rtbh cfg:-**

```sh
route-map rtbh permit 10
 match tag 666
 set community no-export
 set ip next-hop 192.0.2.1
 set local-preference 200
 set origin igp
exit

router bgp 65000
 bgp router-id 10.0.1.7
 no bgp default ipv4-unicast
 neighbor rr peer-group
 neighbor rr remote-as 65000
 neighbor rr update-source 10.0.1.7
 neighbor 10.0.1.1 peer-group rr
 neighbor 10.0.1.2 peer-group rr
 !
 address-family ipv4 unicast
  redistribute static route-map rtbh
  neighbor 10.0.1.1 activate
  neighbor 10.0.1.2 activate
 exit-address-family
exit

ip route 10.10.10.10/32 Null0 tag 666
ip route 192.0.2.1/32 blackhole
```

> 📝 **How this works:** A static discard route to `10.10.10.10/32` is tagged `666`. The `rtbh` route-map matches that tag and, on redistribution into BGP, sets **NO_EXPORT** (so it stays within the AS), rewrites the **next-hop to 192.0.2.1** (the discard next-hop), sets **Local Preference 200** (so it wins best-path everywhere), and forces **Origin IGP**. Every router in the AS with a static discard route to `192.0.2.1` will now black-hole traffic to `10.10.10.10`.

**rtbh op:-**

```log
rtbh# show ip bgp summary 

IPv4 Unicast Summary:
BGP router identifier 10.0.1.7, local AS number 65000 VRF default vrf-id 0
BGP table version 30
RIB entries 9, using 1152 bytes of memory
Peers 2, using 33 KiB of memory
Peer groups 1, using 64 bytes of memory

Neighbor        V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
10.0.1.1        4      65000        74        56       30    0    0 00:30:16            4        1 N/A
10.0.1.2        4      65000       118       101       30    0    0 00:47:48            4        1 N/A

Total number of neighbors 2

rtbh# show ip bgp 
BGP table version is 30, local router ID is 10.0.1.7, vrf id 0
Default local pref 100, local AS 65000
Status codes:  s suppressed, d damped, h history, u unsorted, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>  10.10.10.10/32   192.0.2.1                0    200  32768 i
 *>i 11.11.11.11/32   10.0.1.6                      100      0 65001 i
 * i                  10.0.1.5                 0    100      0 65001 i
 *>i 172.16.1.0/24    10.0.1.3                 0    120      0 65002 i
 *=i                  10.0.1.3                 0    120      0 65002 i
 *>i 172.17.1.0/24    10.0.1.3                 0    100      0 65003 i
 *=i                  10.0.1.3                 0    100      0 65003 i
 *>i 172.18.1.0/24    10.0.1.4                 0    100      0 65004 i
 *=i                  10.0.1.4                 0    100      0 65004 i

Displayed 5 routes and 9 total paths

rtbh# show ip bgp 10.10.10.10
BGP routing table entry for 10.10.10.10/32, version 30
Paths: (1 available, best #1, table default, not advertised to EBGP peer)
  Advertised to non peer-group peers:
  10.0.1.1 10.0.1.2
  Local
    192.0.2.1 from 0.0.0.0 (10.0.1.7)
      Origin IGP, metric 0, localpref 200, weight 32768, tag 666, valid, sourced, best (First path received)
      Community: no-export
      Last update: Thu Jul 23 03:40:56 2026

rtbh# show ip bgp neighbors 10.0.1.1 advertised-routes 10.10.10.10/32       
BGP table version is 30, local router ID is 10.0.1.7, vrf id 0
Default local pref 100, local AS 65000
BGP routing table entry for 10.10.10.10/32, version 30
Paths: (1 available, best #1, table default, not advertised to EBGP peer)
  Advertised to non peer-group peers:
  10.0.1.1 10.0.1.2
  Local
    192.0.2.1 from 0.0.0.0 (10.0.1.7)
      Origin IGP, metric 0, localpref 200, weight 32768, tag 666, valid, sourced, best (First path received)
      Community: no-export
      Last update: Thu Jul 23 03:40:55 2026

Total number of prefixes 1

rtbh# show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "static", distance 1, metric 0, tag 666, best
  Last update 00:15:22 ago
  * unreachable (blackhole), weight 1

rtbh# show ip route 192.0.2.1
Routing entry for 192.0.2.1/32
  Known via "static", distance 1, metric 0, best
  Last update 00:26:13 ago
  * unreachable (blackhole), weight 1
```

**ios-rr1 cfg:-**

```sh
interface Null0
 no ip unreachables
!
ip route 192.0.2.1 255.255.255.255 Null0
```

> 📝 **Every other router in the AS needs this same discard-route config** — a static route to `192.0.2.1` pointed at `Null0`/`discard`. Without it, they'd have nothing to recursively resolve the RTBH next-hop against.

**ios-rr1 op:-**

```log
ios-rr1#show ip bgp 10.10.10.10
BGP routing table entry for 10.10.10.10/32, version 27
Paths: (2 available, best #1, table default, not advertised to EBGP peer)
  Additional-path-install
  Advertised to update-groups:
     7          8          9          10        
  Refresh Epoch 1
  Local, (Received from a RR-client)
    192.0.2.1 from 10.0.1.7 (10.0.1.7)
      Origin IGP, metric 0, localpref 200, valid, internal, best
      Community: no-export
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 23 2026 03:40:55 UTC
  Refresh Epoch 1
  Local
    192.0.2.1 from 10.0.1.2 (10.0.1.2)
      Origin IGP, metric 0, localpref 200, valid, internal
      Community: no-export
      Originator: 10.0.1.7, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 23 2026 03:40:55 UTC

ios-rr1#show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "bgp 65000", distance 200, metric 0, type internal
  Last update from 192.0.2.1 00:06:47 ago
  Routing Descriptor Blocks:
  * 192.0.2.1, from 10.0.1.7, 00:06:47 ago
      opaque_ptr 0x7FFFDDE85660 
      Route metric is 0, traffic share count is 1
      AS Hops 0
      MPLS label: none

ios-rr1#show ip cef 10.10.10.10
10.10.10.10/32
  nexthop 192.0.2.1 Null0
```

**junos-rr2 cfg:-**

```
set routing-options static route 192.0.2.1/32 discard
```

**junos-rr2 op:-**

```log
root@junos-rr2> show route protocol bgp 10.10.10.10 detail 

inet.0: 32 destinations, 38 routes (32 active, 0 holddown, 0 hidden)
10.10.10.10/32 (2 entries, 1 announced)
        *BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaacf91311c
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.7
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaac89bff10 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <Active Int Ext>
                Peer AS: 65000
                Age: 8:27       Metric: 0       Metric2: 0 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.7
                Announcement bits (4): 1-KRT MFS 2-KRT 5-BGP_RT_Background 6-Resolve tree 1 
                AS path: I 
                Communities: no-export
                Accepted
                Localpref: 200
                Router ID: 10.0.1.7
                Thread: junos-main 
         BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaacf91311c
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.1
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaac89bff10 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext>
                Inactive reason: Not Best in its group - Cluster list length
                Peer AS: 65000
                Age: 20:41      Metric: 0       Metric2: 0 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.1
                AS path: I  (Originator)
                Cluster list:  10.0.1.1
                Originator ID: 10.0.1.7
                Accepted
                Localpref: 200
                Router ID: 10.0.1.1     
                Thread: junos-main 

root@junos-rr2> show route 192.0.2.1 

inet.0: 32 destinations, 38 routes (32 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

192.0.2.1/32       *[Static/5] 00:26:22
                       Discard

root@junos-rr2> show route protocol bgp 10.10.10.10           

inet.0: 32 destinations, 38 routes (32 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.10.10.10/32     *[BGP/170] 00:09:13, MED 0, localpref 200, from 10.0.1.7
                      AS path: I, validation-state: unverified
                      to Discard
                    [BGP/170] 00:21:27, MED 0, localpref 200, from 10.0.1.1
                      AS path: I, validation-state: unverified
                      to Discard
```

**ios-ed1 cfg:-**

```sh
interface Null0
 no ip unreachables
!
ip route 192.0.2.1 255.255.255.255 Null0
```

**ios-ed1 op:-**

```log
ios-ed1#show ip bgp 10.10.10.10
BGP routing table entry for 10.10.10.10/32, version 30
Paths: (2 available, best #2, table default, not advertised to EBGP peer)
  Additional-path-install
  Not advertised to any peer
  Refresh Epoch 1
  Local
    192.0.2.1 from 10.0.1.2 (10.0.1.2)
      Origin IGP, metric 0, localpref 200, valid, internal
      Community: no-export
      Originator: 10.0.1.7, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 23 2026 03:40:55 UTC
  Refresh Epoch 1
  Local
    192.0.2.1 from 10.0.1.1 (10.0.1.1)
      Origin IGP, metric 0, localpref 200, valid, internal, best
      Community: no-export
      Originator: 10.0.1.7, Cluster list: 10.0.1.1
      rx pathid: 0x0, tx pathid: 0x0
      Updated on Jul 23 2026 03:40:55 UTC
   
ios-ed1#show ip bgp neighbors 10.0.4.2 advertised-routes 
BGP table version is 30, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>i  11.11.11.11/32   10.0.1.5                 0    100      0 65001 i
 *>   172.17.1.0/24    10.0.6.2                 0             0 65003 i
 *>i  172.18.1.0/24    10.0.1.4                 0    100      0 65004 i

Total number of prefixes 3 

ios-ed1#show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "bgp 65000", distance 200, metric 0, type internal
  Last update from 192.0.2.1 00:12:09 ago
  Routing Descriptor Blocks:
  * 192.0.2.1, from 10.0.1.1, 00:12:09 ago
      opaque_ptr 0x7FFFDDE73490 
      Route metric is 0, traffic share count is 1
      AS Hops 0
      MPLS label: none

ios-ed1#show ip cef 10.10.10.10
10.10.10.10/32
  nexthop 192.0.2.1 Null0
```

> ⚠️ **Note on best-path here:** `10.10.10.10` shows `best #2` on ios-ed1, not #1 — the RTBH route (from Originator 10.0.1.7, LocPref 200) is still the one actually installed/forwarding, but path preference among the two reflected copies (via 10.0.1.1 vs 10.0.1.2) is decided by lower-priority tiebreaks (cluster list length / update source) since LocPref/attributes are otherwise identical between the two RR-reflected copies.

**junos-ed2 cfg:-**

```
set routing-options static route 192.0.2.1/32 discard
```

**junos-ed2 op:-**

```log
root@junos-ed2> show route detail 10.10.10.10 

inet.0: 35 destinations, 40 routes (35 active, 0 holddown, 0 hidden)
10.10.10.10/32 (2 entries, 1 announced)
        *BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaf69117bc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.1
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaaef9c1810 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <Active Int Ext>
                Peer AS: 65000
                Age: 13:56      Metric: 0       Metric2: 0 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.1
                Announcement bits (3): 1-KRT MFS 2-KRT 6-Resolve tree 1 
                AS path: I  (Originator)
                Cluster list:  10.0.1.1
                Originator ID: 10.0.1.7
                Communities: no-export
                Accepted
                Localpref: 200
                Router ID: 10.0.1.1
                Thread: junos-main 
         BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaf69117bc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.2
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaaef9c1810 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext Changed>
                Inactive reason: Not Best in its group - Update source
                Peer AS: 65000
                Age: 13:56      Metric: 0       Metric2: 0 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.2
                AS path: I  (Originator)
                Cluster list:  10.0.1.2
                Originator ID: 10.0.1.7
                Communities: no-export  
                Accepted
                Localpref: 200
                Router ID: 10.0.1.2
                Thread: junos-main 

root@junos-ed2> show route protocol bgp advertising-protocol bgp 10.0.4.6    

inet.0: 35 destinations, 40 routes (35 active, 0 holddown, 0 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
* 11.11.11.11/32          Self                                    65001 I
* 172.17.1.0/24           Self                                    65003 I
* 172.18.1.0/24           Self                                    65004 I



root@junos-ed2> show route 192.0.2.1 

inet.0: 35 destinations, 40 routes (35 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

192.0.2.1/32       *[Static/5] 00:11:37
                       Discard
```

> ⚠️ **Important — RTBH route is deliberately NOT advertised to the customer:** Note `show route protocol bgp advertising-protocol bgp 10.0.4.6` on junos-ed2 lists only `11.11.11.11/32`, `172.17.1.0/24`, `172.18.1.0/24` — **not** `10.10.10.10/32`. This confirms the **NO_EXPORT** community is doing its job: the black-hole trigger stays internal to AS 65000 and is never leaked to the eBGP customer (inet-ceos), which only sees the effect (unreachability), not the RTBH signaling itself.

**ios-pe1 cfg:-**

```sh
interface Null0
 no ip unreachables
!
ip route 192.0.2.1 255.255.255.255 Null0
```

**ios-pe1 op:-**

```log
ios-pe1#show ip bgp 
BGP table version is 33, local router ID is 10.0.1.5
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>i  10.10.10.10/32   192.0.2.1                0    200      0 i
 *b                    10.0.5.2                      120      0 65001 i
 * i                   192.0.2.1                0    200      0 i
 *>   11.11.11.11/32   10.0.5.2                               0 65001 i
 *bi                   10.0.1.6                      100      0 65001 i
 *>i  172.16.1.0/24    10.0.1.3                 0    120      0 65002 i
 * i                   10.0.1.3                 0    120      0 65002 i
 * i  172.17.1.0/24    10.0.1.3                 0    100      0 65003 i
 *>i                   10.0.1.3                 0    100      0 65003 i
 *>i  172.18.1.0/24    10.0.1.4                 0    100      0 65004 i
 * i                   10.0.1.4                 0    100      0 65004 i

ios-pe1#show ip bgp 10.10.10.10
BGP routing table entry for 10.10.10.10/32, version 35
Paths: (3 available, best #1, table default, not advertised to EBGP peer)
  Additional-path-install
  Not advertised to any peer
  Refresh Epoch 1
  Local
    192.0.2.1 from 10.0.1.1 (10.0.1.1)
      Origin IGP, metric 0, localpref 200, valid, internal, best
      Community: no-export
      Originator: 10.0.1.7, Cluster list: 10.0.1.1
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 23 2026 03:40:55 UTC
  Refresh Epoch 1
  65001
    10.0.5.2 from 10.0.5.2 (10.0.5.2)
      Origin IGP, localpref 120, valid, external, backup/repair
      Community: 65001:120 65001:1001 , recursive-via-connected
      rx pathid: 0, tx pathid: 0
      Updated on Jul 23 2026 03:14:22 UTC
  Refresh Epoch 1
  Local
    192.0.2.1 from 10.0.1.2 (10.0.1.2)
      Origin IGP, metric 0, localpref 200, valid, internal
      Community: no-export
      Originator: 10.0.1.7, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 23 2026 03:40:55 UTC

ios-pe1#show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "bgp 65000", distance 200, metric 0, type internal
  Last update from 192.0.2.1 00:07:11 ago
  Routing Descriptor Blocks:
  * 192.0.2.1, from 10.0.1.1, 00:07:11 ago
      opaque_ptr 0x7FFFDDE4DB80 
      Route metric is 0, traffic share count is 1
      AS Hops 0
      MPLS label: none

ios-pe1#show ip cef 10.10.10.10
10.10.10.10/32
  nexthop 192.0.2.1 Null0
```

> 📝 **Interesting result here:** even though `10.10.10.10/32` is *also* a real customer route learned via eBGP (65001, from 10.0.5.2), the RTBH-injected iBGP path with **LocPref 200** beats it easily — RTBH deliberately outranks the legitimate route so the black-hole always wins for as long as it's active.

**junos-pe2 cfg:-**

```
set routing-options static route 192.0.2.1/32 discard
```

**junos-pe2 op:-**

```log
root@junos-pe2> show route protocol bgp   

inet.0: 33 destinations, 39 routes (33 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.10.10.10/32     *[BGP/170] 00:07:46, MED 0, localpref 200, from 10.0.1.1
                      AS path: I, validation-state: unverified
                      to Discard
                    [BGP/170] 00:07:45, MED 0, localpref 200, from 10.0.1.2
                      AS path: I, validation-state: unverified
                      to Discard
                    [BGP/170] 00:40:47, localpref 120
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.5.6 via eth4
11.11.11.11/32     *[BGP/170] 00:40:47, localpref 100
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.5.6 via eth4
                    [BGP/170] 00:22:05, MED 0, localpref 100, from 10.0.1.1
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.3.9 via eth3
172.16.1.0/24      *[BGP/170] 00:22:55, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.5 via eth1
                    [BGP/170] 00:22:55, MED 0, localpref 120, from 10.0.1.2
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.5 via eth1
172.17.1.0/24      *[BGP/170] 00:22:55, MED 0, localpref 100, from 10.0.1.1
                      AS path: 65003 I, validation-state: unverified
                    >  to 10.0.3.5 via eth1
                    [BGP/170] 00:22:55, MED 0, localpref 100, from 10.0.1.2
                      AS path: 65003 I, validation-state: unverified
                    >  to 10.0.3.5 via eth1
172.18.1.0/24      *[BGP/170] 00:22:58, MED 0, localpref 100, from 10.0.1.1
                      AS path: 65004 I, validation-state: unverified
                    >  to 10.0.3.5 via eth1
                    [BGP/170] 00:40:33, MED 0, localpref 100, from 10.0.1.2
                      AS path: 65004 I, validation-state: unverified
                    >  to 10.0.3.5 via eth1

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)

root@junos-pe2> show route detail 10.10.10.10 

inet.0: 33 destinations, 39 routes (33 active, 0 holddown, 0 hidden)
10.10.10.10/32 (3 entries, 1 announced)
        *BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaf59117bc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.1
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaaee9bb690 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <Active Int Ext>
                Peer AS: 65000
                Age: 18:28      Metric: 0       Metric2: 0 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.1
                Announcement bits (3): 1-KRT MFS 2-KRT 6-Resolve tree 1 
                AS path: I  (Originator)
                Cluster list:  10.0.1.1
                Originator ID: 10.0.1.7
                Communities: no-export
                Accepted
                Localpref: 200
                Router ID: 10.0.1.1
                Thread: junos-main 
         BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaf59117bc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.2
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaaee9bb690 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext Changed>
                Inactive reason: Not Best in its group - Update source
                Peer AS: 65000
                Age: 18:28      Metric: 0       Metric2: 0 
                Validation State: unverified 
                Task: BGP_65000_65000.10.0.1.2
                AS path: I  (Originator)
                Cluster list:  10.0.1.2
                Originator ID: 10.0.1.7
                Communities: no-export  
                Accepted
                Localpref: 200
                Router ID: 10.0.1.2
                Thread: junos-main 
         BGP    Preference: 170/-121
                Next hop type: Router, Next hop index: 0
                Address: 0xaaaaee8dc19c
                Next-hop reference count: 3, Next-hop session id: 0
                Kernel Table Id: 0
                Source: 10.0.5.6
                Next hop: 10.0.5.6 via eth4, selected
                Session Id: 0
                State: <Ext>
                Inactive reason: Local Preference
                Peer AS: 65001
                Age: 1:03:43 
                Validation State: unverified 
                Task: BGP_65001_65000.10.0.5.6
                AS path: 65001 I 
                Communities: 65001:120 65001:1002
                Accepted
                Localpref: 120
                Router ID: 10.0.5.6
                Thread: junos-main 

root@junos-pe2> show route 10.10.10.10 

inet.0: 33 destinations, 39 routes (33 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.10.10.10/32     *[BGP/170] 00:18:46, MED 0, localpref 200, from 10.0.1.1
                      AS path: I, validation-state: unverified
                      to Discard
                    [BGP/170] 00:18:46, MED 0, localpref 200, from 10.0.1.2
                      AS path: I, validation-state: unverified
                      to Discard
                    [BGP/170] 01:04:01, localpref 120
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.5.6 via eth4
```

**inet-ceos op:-**

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
 * >      11.11.11.11/32         10.0.4.1              0       -          120     0       65000 65001 i
 *        11.11.11.11/32         10.0.4.5              0       -          100     0       65000 65001 i
 * >      172.16.1.0/24          -                     -       -          -       0       i
 * >      172.17.1.0/24          10.0.4.1              0       -          120     0       65000 65003 i
 *        172.17.1.0/24          10.0.4.5              0       -          100     0       65000 65003 i
 * >      172.18.1.0/24          10.0.4.1              0       -          120     0       65000 65004 i
 *        172.18.1.0/24          10.0.4.5              0       -          100     0       65000 65004 i
```

> ✅ **Confirmed result:** `10.10.10.10/32` no longer appears at all in the customer's (inet-ceos) BGP table — the prefix has been completely black-holed within AS 65000, and the customer-facing router never even sees it (thanks to NO_EXPORT). Traffic destined to `10.10.10.10` is now silently discarded at whichever AS-65000 edge router it enters.

---

### Community Attribute Based RTBH (Lab)

- **Customer Router Signaled** — this time, the customer's own router (bird3-1, an eBGP peer) sends the community, rather than the ISP's trigger router originating it directly.

#### Before Config

**ios-pe1 op:-**

```log
ios-pe1#show ip bgp 10.10.10.10
BGP routing table entry for 10.10.10.10/32, version 34
Paths: (2 available, best #2, table default)
  Additional-path-install
  Advertised to update-groups:
     6          7
  Refresh Epoch 1
  65001
    10.0.1.6 (metric 1) from 10.0.1.2 (10.0.1.2)
      Origin IGP, localpref 120, valid, internal, backup/repair
      Community: 65001:120 65001:1002
      Originator: 10.0.1.6, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 25 2026 07:00:19 UTC
  Refresh Epoch 15
  65001
    10.0.5.2 from 10.0.5.2 (10.0.5.2)
      Origin IGP, localpref 120, valid, external, best
      Community: 65001:120 65001:1001 , recursive-via-connected
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 25 2026 06:55:20 UTC


ios-pe1#show ip bgp neighbors 10.0.1.1 advertised-routes 10.10.10.10/32 <<<< Advertise toward rr1
BGP routing table entry for 10.10.10.10/32, version 34
  Paths: (2 available, best #2, table default)
  Advertised Attributes
    Local Preference: 120
    Metric: 0
    Origin: IGP
    AS-Path:  65001
    Community: 65001:120 65001:1001
    Nexthop: 10.0.1.5


ios-pe1#show ip bgp neighbors 10.0.1.2 advertised-routes 10.10.10.10/32 <<<< Advertise toward rr2
BGP routing table entry for 10.10.10.10/32, version 34
  Paths: (2 available, best #2, table default)
  Advertised Attributes
    Local Preference: 120
    Metric: 0
    Origin: IGP
    AS-Path:  65001
    Community: 65001:120 65001:1001
    Nexthop: 10.0.1.5
```

**junos-pe1 op:-**

```log
root@junos-pe2> show route 10.10.10.10/32
inet.0: 33 destinations, 38 routes (33 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.10.10.10/32     *[BGP/170] 00:06:12, localpref 120
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.5.6 via eth4
                    [BGP/170] 00:06:11, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.3.9 via eth3

root@junos-pe2> show route advertising-protocol bgp 10.0.1.1 10.10.10.10/32 detail  <<<< Advertise toward rr1
inet.0: 33 destinations, 38 routes (33 active, 0 holddown, 0 hidden)
* 10.10.10.10/32 (2 entries, 1 announced)
 BGP group rr-srv type Internal
     Nexthop: Self
     Flags: Nexthop Change
     Localpref: 120
     AS path: [65000] 65001 I
     Communities: 65001:120 65001:1002

root@junos-pe2> show route advertising-protocol bgp 10.0.1.2 10.10.10.10/32 detail  <<<< Advertise toward rr2
inet.0: 33 destinations, 38 routes (33 active, 0 holddown, 0 hidden)
* 10.10.10.10/32 (2 entries, 1 announced)
 BGP group rr-srv type Internal
     Nexthop: Self
     Flags: Nexthop Change
     Localpref: 120
     AS path: [65000] 65001 I
     Communities: 65001:120 65001:1002
```

**ios-rr1 op:-**

```log
ios-rr1#show ip bgp 10.10.10.10/32
BGP routing table entry for 10.10.10.10/32, version 38
Paths: (3 available, best #1, table default)
  Additional-path-install
  Advertised to update-groups:
     1          3          4          5
  Refresh Epoch 4
  65001, (Received from a RR-client)
    10.0.1.5 (metric 2) from 10.0.1.5 (10.0.1.5)
      Origin IGP, metric 0, localpref 120, valid, internal, best
      Community: 65001:120 65001:1001
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 25 2026 07:00:19 UTC
  Refresh Epoch 1
  65001
    10.0.1.6 (metric 2) from 10.0.1.2 (10.0.1.2)
      Origin IGP, localpref 120, valid, internal
      Community: 65001:120 65001:1002
      Originator: 10.0.1.6, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 25 2026 07:00:19 UTC
  Refresh Epoch 1
  65001, (Received from a RR-client)
    10.0.1.6 (metric 2) from 10.0.1.6 (10.0.1.6)
      Origin IGP, localpref 120, valid, internal, backup/repair
      Community: 65001:120 65001:1002
      rx pathid: 0, tx pathid: 0
      Updated on Jul 25 2026 07:00:19 UTC

ios-rr1#show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "bgp 65000", distance 200, metric 0
  Tag 65001, type internal
  Last update from 10.0.1.5 00:10:21 ago
  Routing Descriptor Blocks:
  * 10.0.1.5, from 10.0.1.5, 00:10:21 ago
      opaque_ptr 0x7FFFDDE80D28
      Route metric is 0, traffic share count is 1
      AS Hops 1
      Route tag 65001
      MPLS label: none

ios-rr1#show ip cef 10.10.10.10
10.10.10.10/32
  nexthop 10.0.2.10 Ethernet0/
```

**junos-rr2 op:-**

```log
root@junos-rr2> show route detail 10.10.10.10

inet.0: 32 destinations, 39 routes (32 active, 0 holddown, 0 hidden)
10.10.10.10/32 (3 entries, 1 announced)
        *BGP    Preference: 170/-121
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaefcdac9c
                Next-hop reference count: 4
                Kernel Table Id: 0
                Source: 10.0.1.6
                Next hop type: Router, Next hop index: 0
                Next hop: 10.0.2.14 via eth2, selected
                Session Id: 0
                Protocol next hop: 10.0.1.6
                Indirect next hop: 0xaaaaefdbf290 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <Active Int Ext>
                Peer AS: 65000
                Age: 12:12      Metric2: 1
                Validation State: unverified
                Task: BGP_65000_65000.10.0.1.6
                Announcement bits (4): 1-KRT MFS 2-KRT 6-BGP_RT_Background 7-Resolve tree 1
                AS path: 65001 I
                Communities: 65001:120 65001:1002
                Accepted
                Localpref: 120
                Router ID: 10.0.1.6
                Thread: junos-main
         BGP    Preference: 170/-121
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaefce20fc
                Next-hop reference count: 4
                Kernel Table Id: 0
                Source: 10.0.1.5
                Next hop type: Router, Next hop index: 0
                Next hop: 10.0.2.1 via eth1, selected
                Session Id: 0
                Next hop: 10.0.2.14 via eth2
                Session Id: 0
                Protocol next hop: 10.0.1.5
                Indirect next hop: 0xaaaaefdbf010 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext Changed>
                Inactive reason: Not Best in its group - IGP metric
                Peer AS: 65000
                Age: 12:12      Metric: 0       Metric2: 3
                Validation State: unverified
                Task: BGP_65000_65000.10.0.1.5
                AS path: 65001 I
                Communities: 65001:120 65001:1001
                Accepted
                Localpref: 120
                Router ID: 10.0.1.5
                Thread: junos-main
         BGP    Preference: 170/-121
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaefce20fc
                Next-hop reference count: 4
                Kernel Table Id: 0
                Source: 10.0.1.1
                Next hop type: Router, Next hop index: 0
                Next hop: 10.0.2.1 via eth1, selected
                Session Id: 0
                Next hop: 10.0.2.14 via eth2
                Session Id: 0
                Protocol next hop: 10.0.1.5
                Indirect next hop: 0xaaaaefdbf010 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext Changed>
                Inactive reason: Not Best in its group - IGP metric
                Peer AS: 65000
                Age: 12:12      Metric: 0       Metric2: 3
                Validation State: unverified
                Task: BGP_65000_65000.10.0.1.1
                AS path: 65001 I  (Originator)
                Cluster list:  10.0.1.1
                Originator ID: 10.0.1.5
                Accepted
                Localpref: 120
                Router ID: 10.0.1.1
                Thread: junos-main
```

**inet-ceos op:-**

```log
inet-ceos#show ip bgp 10.10.10.10
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
BGP routing table entry for 10.10.10.10/32
 Paths: 2 available
  65000 65001
    10.0.4.1 from 10.0.4.1 (10.0.1.3)
      Origin IGP, metric 0, localpref 120, IGP metric 0, weight 0, tag 0
      Received 00:13:23 ago, valid, external, best
      Community: 65001:120 65001:1001
      Rx path id: 0x0
      Rx SAFI: Unicast
  65000 65001
    10.0.4.5 from 10.0.4.5 (10.0.1.4)
      Origin IGP, metric 0, localpref 100, IGP metric 0, weight 0, tag 0
      Received 00:13:52 ago, valid, external
      Community: 65001:120 65001:1002
      Rx SAFI: Unicast

inet-ceos#show ip route 10.10.10.10
VRF: default
Source Codes:
       C - connected, S - static, K - kernel,
       O - OSPF, O IA - OSPF inter area, O E1 - OSPF external type 1,
       O E2 - OSPF external type 2, O N1 - OSPF NSSA external type 1,
       O N2 - OSPF NSSA external type2, O3 - OSPFv3,
       O3 IA - OSPFv3 inter area, O3 E1 - OSPFv3 external type 1,
       O3 E2 - OSPFv3 external type 2,
       O3 N1 - OSPFv3 NSSA external type 1,
       O3 N2 - OSPFv3 NSSA external type2, B - Other BGP Routes,
       B I - iBGP, B E - eBGP, R - RIP, I L1 - IS-IS level 1,
       I L2 - IS-IS level 2, A B - BGP Aggregate,
       A O - OSPF Summary, NG - Nexthop Group Static Route,
       V - VXLAN Control Service, M - Martian,
       DH - DHCP client installed default route,
       DP - Dynamic Policy Route, L - VRF Leaked,
       G  - gRIBI, RC - Route Cache Route,
       CL - CBF Leaked Route

 B E      10.10.10.10/32 [200/0]
           via 10.0.4.1, Ethernet1
```

#### After Config and Community sent from bird3-1 peer

**ios-pe1 cfg:-**

```sh
ip community-list standard bird3-65001-1 permit 65001:120
ip community-list standard bird3-65001-2 permit 65001:80
ip community-list standard bird3-65001-rtbh permit 65001:666
!
route-map bird3-65001 permit 1
 match community bird3-65001-1
 set local-preference 120
route-map bird3-65001 permit 2
 match community bird3-65001-2
 set local-preference 80
route-map bird3-65001 permit 3
 match community bird3-65001-rtbh
 set local-preference 200
 set community no-export additive
route-map bird3-65001 permit 4
 match ip address prefix-list bird3-1
!
route-map to-rr permit 10
 match community bird3-65001-rtbh
 set ip next-hop 192.0.2.1
route-map to-rr permit 20
 set ip next-hop self
!
ip prefix-list bird3-1 seq 1 permit 10.10.10.10/32
ip prefix-list bird3-1 seq 2 permit 11.11.11.11/32
!
router bgp 65000
 template peer-policy rr-srv
  route-map to-rr out
  send-community both
 exit-peer-policy
 !
 template peer-session rr-srv
  remote-as 65000
  update-source Loopback0
 exit-peer-session
 !
 bgp router-id 10.0.1.5
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.0.1.1 inherit peer-session rr-srv
 neighbor 10.0.1.2 inherit peer-session rr-srv
 neighbor 10.0.5.2 remote-as 65001
 !
 address-family ipv4
  bgp additional-paths install
  neighbor 10.0.1.1 activate
  neighbor 10.0.1.1 inherit peer-policy rr-srv
  neighbor 10.0.1.2 activate
  neighbor 10.0.1.2 inherit peer-policy rr-srv
  neighbor 10.0.5.2 activate
  neighbor 10.0.5.2 route-map bird3-65001 in
 exit-address-family
!
ip bgp-community new-format
```

> 📝 **How this differs from the next-hop-based lab:** Here, the ISP edge router (ios-pe1) accepts communities **from the customer (bird3-1)** and reacts to them — `65001:120`/`65001:80` set normal local-pref tiers, but `65001:666` is defined as the customer's **RTBH trigger community**. When matched, it sets LocPref 200 **and** adds NO_EXPORT — then a separate outbound route-map (`to-rr`) rewrites the next-hop to `192.0.2.1` specifically for routes carrying that RTBH community, while every other route just gets `next-hop self` as normal.

**junos-pe1 cfg:-**

```sh
set policy-options community bird3-65001-1 members 65001:120
set policy-options community bird3-65001-2 members 65001:80
set policy-options community bird3-65001-rtbh members 65001:666
set policy-options community no-export members no-export
#
set policy-options prefix-list bird3-65001 10.10.10.10/32
set policy-options prefix-list bird3-65001 11.11.11.11/32
#
set policy-options policy-statement bird3-65001 term 1 from community bird3-65001-1
set policy-options policy-statement bird3-65001 term 1 then local-preference 120
set policy-options policy-statement bird3-65001 term 1 then accept
set policy-options policy-statement bird3-65001 term 2 from community bird3-65001-2
set policy-options policy-statement bird3-65001 term 2 then local-preference 80
set policy-options policy-statement bird3-65001 term 2 then accept
set policy-options policy-statement bird3-65001 term 3 from community bird3-65001-rtbh
set policy-options policy-statement bird3-65001 term 3 then local-preference 200
set policy-options policy-statement bird3-65001 term 3 then community + no-export
set policy-options policy-statement bird3-65001 term 3 then accept
set policy-options policy-statement bird3-65001 term 4 from prefix-list bird3-65001
set policy-options policy-statement bird3-65001 term 4 then accept
set policy-options policy-statement bird3-65001 term 10 then reject
#
set policy-options policy-statement to-ibgp term 0 from community bird3-65001-rtbh
set policy-options policy-statement to-ibgp term 0 then next-hop 192.0.2.1
set policy-options policy-statement to-ibgp term 0 then accept
set policy-options policy-statement to-ibgp term 1 from protocol bgp
set policy-options policy-statement to-ibgp term 1 then next-hop self
set policy-options policy-statement to-ibgp term 1 then accept
set policy-options policy-statement to-ibgp term 10 then reject
#
set protocols bgp group bird3-2 local-address 10.0.5.5
set protocols bgp group bird3-2 import bird3-65001
set protocols bgp group bird3-2 peer-as 65001
set protocols bgp group bird3-2 local-as 65000
set protocols bgp group bird3-2 neighbor 10.0.5.6
set protocols bgp group rr-srv local-address 10.0.1.6
set protocols bgp group rr-srv export to-ibgp
set protocols bgp group rr-srv peer-as 65000
set protocols bgp group rr-srv local-as 65000
set protocols bgp group rr-srv neighbor 10.0.1.1
set protocols bgp group rr-srv neighbor 10.0.1.2
set protocols bgp bgp-identifier 10.0.1.6
```

In RR and other ISP devices, we need to configure static routes towards Null0:

**Cisco config:-**

```sh
interface Null0
 no ip unreachables

ip route 192.0.2.1 255.255.255.255 Null0
```

**Junos config:-**

```sh
set routing-options static route 192.0.2.1/32 discard
```

**Bird3-1 sending routes with community 65001:666:-**

```log
bird> show route export to_pe1 all
Table master4:
10.10.10.10/32       unicast [direct1 04:45:07.515] * (240)
        dev any0
        preference: 240
        source: device
        bgp_community: (65001,666) (65001,1001)
        Internal route handling values: 3L 4G 0S id 1
11.11.11.11/32       unicast [direct1 04:45:07.515] * (240)
        dev any0
        preference: 240
        source: device
        bgp_community: (65001,1001)
        Internal route handling values: 3L 4G 0S id 2
```

> 📝 Note that `10.10.10.10/32` is signaled with community `65001:666` (the RTBH trigger), while `11.11.11.11/32` is only tagged `65001:1001` (a normal identification community) — only the first prefix should get black-holed.

**ios-pe1 op:-**

```log
ios-pe1#show ip bgp 10.10.10.10/32  
BGP routing table entry for 10.10.10.10/32, version 36
Paths: (1 available, best #1, table default, not advertised to EBGP peer)
  Additional-path-install
  Advertised to update-groups:
     6          7
  Refresh Epoch 16
  65001
    10.0.5.2 from 10.0.5.2 (10.0.5.2)
      Origin IGP, localpref 200, valid, external, best
      Community: 65001:666 65001:1001 no-export , recursive-via-connected
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 25 2026 07:23:56 UTC

ios-pe1#show ip bgp neighbors 10.0.1.1 advertised-routes 10.10.10.10/32 <<<< Advertise toward rr1
BGP routing table entry for 10.10.10.10/32, version 36
  Paths: (1 available, best #1, table default)
  Advertised Attributes
    Local Preference: 200
    Metric: 0
    Origin: IGP
    AS-Path:  65001
    Community: 65001:666 65001:1001 no-export
    Nexthop: 10.0.5.2

ios-pe1#show ip bgp neighbors 10.0.1.2 advertised-routes 10.10.10.10/32 <<<< Advertise toward rr1
BGP routing table entry for 10.10.10.10/32, version 36
  Paths: (1 available, best #1, table default)
  Advertised Attributes
    Local Preference: 200
    Metric: 0
    Origin: IGP
    AS-Path:  65001
    Community: 65001:666 65001:1001 no-export
    Nexthop: 10.0.5.2
```

**junos-pe2 op:-**

```log
root@junos-pe2> show route 10.10.10.10/30

inet.0: 33 destinations, 39 routes (33 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

10.10.10.10/32     *[BGP/170] 00:06:18, MED 0, localpref 200, from 10.0.1.1
                      AS path: 65001 I, validation-state: unverified
                      to Discard
                    [BGP/170] 00:06:18, MED 0, localpref 200, from 10.0.1.2
                      AS path: 65001 I, validation-state: unverified
                      to Discard
                    [BGP/170] 00:29:55, localpref 120
                      AS path: 65001 I, validation-state: unverified
                    >  to 10.0.5.6 via eth4

root@junos-pe2> show route advertising-protocol bgp 10.0.1.1 10.10.10.10/32 detail

root@junos-pe2> show route advertising-protocol bgp 10.0.1.2 10.10.10.10/32 detail
```

**ios-rr1 op:-**

```log
ios-rr1#show ip bgp neighbors 10.0.1.5 received-routes
BGP table version is 41, local router ID is 10.0.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>i  10.10.10.10/32   192.0.2.1                0    200      0 65001 i
 *>i  11.11.11.11/32   10.0.1.5                 0    100      0 65001 i

ios-rr1#show ip bgp neighbors 10.0.1.6 received-routes
BGP table version is 41, local router ID is 10.0.1.1
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *bi  11.11.11.11/32   10.0.1.6                      100      0 65001 i

Total number of prefixes 1

ios-rr1#show ip bgp 10.10.10.10/32
BGP routing table entry for 10.10.10.10/32, version 41
Paths: (2 available, best #1, table default, not advertised to EBGP peer)
  Additional-path-install
  Advertised to update-groups:
     1          3          4          5
  Refresh Epoch 4
  65001, (Received from a RR-client)
    192.0.2.1 from 10.0.1.5 (10.0.1.5)
      Origin IGP, metric 0, localpref 200, valid, internal, best
      Community: 65001:666 65001:1001 no-export
      rx pathid: 0, tx pathid: 0x0
      Updated on Jul 25 2026 07:23:56 UTC
  Refresh Epoch 1
  65001
    192.0.2.1 from 10.0.1.2 (10.0.1.2)
      Origin IGP, metric 0, localpref 200, valid, internal
      Community: 65001:666 65001:1001 no-export
      Originator: 10.0.1.5, Cluster list: 10.0.1.2
      rx pathid: 0, tx pathid: 0
      Updated on Jul 25 2026 07:23:56 UTC

ios-rr1#show ip route 10.10.10.10
Routing entry for 10.10.10.10/32
  Known via "bgp 65000", distance 200, metric 0
  Tag 65001, type internal
  Last update from 192.0.2.1 00:08:02 ago
  Routing Descriptor Blocks:
  * 192.0.2.1, from 10.0.1.5, 00:08:02 ago
      opaque_ptr 0x7FFFDDE810E8
      Route metric is 0, traffic share count is 1
      AS Hops 1
      Route tag 65001
      MPLS label: none

ios-rr1#show ip cef 10.10.10.10
10.10.10.10/32
  nexthop 192.0.2.1 Null0
```

**junos-rr2 op:-**

```log
root@junos-rr2> show route receive-protocol bgp 10.0.1.5
inet.0: 32 destinations, 38 routes (32 active, 0 holddown, 0 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
* 10.10.10.10/32          192.0.2.1            0       200        65001 I
  11.11.11.11/32          10.0.1.5             0       100        65001 I

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)
root@junos-rr2> show route receive-protocol bgp 10.0.1.6

inet.0: 32 destinations, 38 routes (32 active, 0 holddown, 0 hidden)
  Prefix                  Nexthop              MED     Lclpref    AS path
* 11.11.11.11/32          10.0.1.6                     100        65001 I

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)

root@junos-rr2> show route detail 10.10.10.10/32
inet.0: 32 destinations, 38 routes (32 active, 0 holddown, 0 hidden)
10.10.10.10/32 (2 entries, 1 announced)
        *BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaf6d10fdc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.5
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaaefdbc090 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <Active Int Ext>
                Peer AS: 65000
                Age: 8:55       Metric: 0       Metric2: 0
                Validation State: unverified
                Task: BGP_65000_65000.10.0.1.5
                Announcement bits (4): 1-KRT MFS 2-KRT 6-BGP_RT_Background 7-Resolve tree 1
                AS path: 65001 I
                Communities: 65001:666 65001:1001 no-export
                Accepted
                Localpref: 200
                Router ID: 10.0.1.5
                Thread: junos-main
         BGP    Preference: 170/-201
                Next hop type: Indirect, Next hop index: 0
                Address: 0xaaaaf6d10fdc
                Next-hop reference count: 3
                Kernel Table Id: 0
                Source: 10.0.1.1
                Next hop type: Discard, Next hop index: 0
                Protocol next hop: 192.0.2.1
                Indirect next hop: 0xaaaaefdbc090 - INH Session ID: 0, INH non-key opaque: (nil), INH key opaque: (nil)
                State: <NotBest Int Ext>
                Inactive reason: Not Best in its group - Cluster list length
                Peer AS: 65000
                Age: 8:55       Metric: 0       Metric2: 0
                Validation State: unverified
                Task: BGP_65000_65000.10.0.1.1
                AS path: 65001 I  (Originator)
                Cluster list:  10.0.1.1
                Originator ID: 10.0.1.5
                Accepted
                Localpref: 200
                Router ID: 10.0.1.1
                Thread: junos-main
```

**inet-ceos op:-**

```log
inet-ceos#show ip bgp neighbors 10.0.4.1 received-routes
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Route status codes: s - suppressed contributor, * - valid, > - active, E - ECMP head, e - ECMP
                    S - Stale, c - Contributing to ECMP, b - backup, L - labeled-unicast, q - Pending FIB install
                    % - Pending best path selection
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI Origin Validation codes: V - valid, I - invalid, U - unknown
AS Path Attributes: Or-ID - Originator ID, C-LST - Cluster List, LL Nexthop - Link Local Nexthop

          Network                Next Hop              Metric  AIGP       LocPref Weight  Path
 * >      11.11.11.11/32         10.0.4.1              -       -          -       -       65000 65001 i
 * >      172.17.1.0/24          10.0.4.1              -       -          -       -       65000 65003 i
 * >      172.18.1.0/24          10.0.4.1              -       -          -       -       65000 65004 i
inet-ceos#show ip bgp neighbors 10.0.4.5 received-routes
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Route status codes: s - suppressed contributor, * - valid, > - active, E - ECMP head, e - ECMP
                    S - Stale, c - Contributing to ECMP, b - backup, L - labeled-unicast, q - Pending FIB install
                    % - Pending best path selection
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI Origin Validation codes: V - valid, I - invalid, U - unknown
AS Path Attributes: Or-ID - Originator ID, C-LST - Cluster List, LL Nexthop - Link Local Nexthop

          Network                Next Hop              Metric  AIGP       LocPref Weight  Path
 *        11.11.11.11/32         10.0.4.5              -       -          -       -       65000 65001 i
 *        172.17.1.0/24          10.0.4.5              -       -          -       -       65000 65003 i
 *        172.18.1.0/24          10.0.4.5              -       -          -       -       65000 65004 i
```

> ✅ **Confirmed result:** just as in the trigger-router-originated lab, `10.10.10.10/32` is completely absent from the customer-facing router's received routes — the black-hole triggered by the customer's own community tag propagates through the ISP's iBGP and takes effect network-wide, while `11.11.11.11/32` (not tagged with `65001:666`) is completely unaffected.

> 💡 **Key difference Community based vs Next-Hop based RTBH:** In the Next-Hop lab, the **ISP's own trigger router** originated the black-hole (via a locally configured static route + tag). In this Community-based lab, the **customer's router (bird3-1)** signals the RTBH request directly over the live eBGP session — giving the customer self-service control to trigger/un-trigger the black-hole without needing to call the ISP's NOC.

---

## References

- [RFC 5635 — Remote Triggered Black Hole Filtering with BGP](https://tools.ietf.org/html/rfc5635)
- [RFC 3704 — Ingress Filtering for Multihomed Networks](https://tools.ietf.org/html/rfc3704)
- [RFC 3882 — Configuring BGP to Block Denial-of-Service Attacks](https://tools.ietf.org/html/rfc3882)
- [RFC 6666 — A Discard Prefix for IPv6](https://tools.ietf.org/html/rfc6666)
- [RFC 7999 — BLACKHOLE Community](https://tools.ietf.org/html/rfc7999)
- [RFC 5575 — Dissemination of Flow Specification Rules](https://tools.ietf.org/html/rfc5575)
- [NTT — Routing Policy / Blackhole Community Example](https://www.gin.ntt.net/support-center/policies-procedures/routing/?utm_source=chatgpt.com)
