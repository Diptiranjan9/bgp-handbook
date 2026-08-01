## BGP TTL & Security Mechanisms

> 💡 **TL;DR:** eBGP defaults to TTL 1 (assumes direct connection). Use `ebgp-multihop` when peers are multiple hops apart, and `ttl-security` (GTSM) to protect against spoofed packets. Don't configure both on the same session.

Related: [[iBGP vs eBGP]]

---

### What is TTL?

TTL (Time To Live) is an IP header field that limits how many Layer 3 hops a packet can traverse. Each router decrements the TTL by 1. When it reaches 0, the packet is discarded (the router typically replies with an ICMP "Time Exceeded" message).

### Default TTL Values

| BGP Session Type | Default TTL | Why |
|---|---:|---|
| eBGP | 1 | Peers assumed directly connected |
| iBGP | 255 | Peers may be multiple hops apart (e.g., loopback-to-loopback) within the same AS |

---

### `ebgp-multihop`

Allows an eBGP session between routers that are **not directly connected**, by raising the TTL used on outgoing packets for that session (instead of the default 1).

```cisco
neighbor <ip> ebgp-multihop <ttl-count>
```

**Use case:** peering over loopback interfaces, or when redundant/multiple physical paths exist between eBGP neighbors.

> ⚠️ **Gotcha:** Raising the TTL removes eBGP's built-in single-hop protection, making the session more exposed to spoofing from remote sources. If security matters, pair the design intent with `ttl-security` instead — see mutual exclusivity note below.

#### sample output of ebgp-multihop

```log
iol1#show ip int br | ex unass
Interface              IP-Address      OK? Method Status                Protocol
Ethernet0/0            100.64.1.2      YES NVRAM  up                    up
Ethernet0/1            172.31.1.1      YES NVRAM  up                    up
Loopback0              172.31.255.2    YES manual up                    up
```

```log
iol1#sh run | sec bgp
router bgp 131074
 bgp router-id 172.31.255.2
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 172.31.255.3 remote-as 196611
 neighbor 172.31.255.3 ebgp-multihop 2
 neighbor 172.31.255.3 update-source Loopback0
 !
 address-family ipv4
  neighbor 172.31.255.3 activate
 exit-address-family
```

```log
iol1#show ip bgp neighbors 172.31.255.3
BGP neighbor is 172.31.255.3,  remote AS 196611, external link
  BGP version 4, remote router ID 172.31.255.3
  BGP state = Established, up for 00:07:57
  Last read 00:00:02, last write 00:00:50, hold time is 180, keepalive interval is 60 seconds
  Last update received: never
  Neighbor sessions:
    1 active, is not multisession capable (disabled)
  Neighbor capabilities:
    Route refresh: advertised and received(new)
    Four-octets ASN Capability: advertised and received
    Address family IPv4 Unicast: advertised and received
    Graceful Restart Capability: received
      Remote Restart timer is 300 seconds
      N bit (graceful-restart extended): received
      Address families advertised by peer:
        none
    Enhanced Refresh Capability: advertised and received
    Multisession Capability:
    Stateful switchover support enabled: NO for session 1
  Message statistics:
    InQ depth is 0
    OutQ depth is 0

                         Sent       Rcvd
    Opens:                  1          1
    Notifications:          0          0
    Updates:                1          0
    Keepalives:            10         11
    Route Refresh:          0          0
    Total:                 12         12
  Do log neighbor state changes (via global configuration)
  Default minimum time between advertisement runs is 30 seconds

 For address family: IPv4 Unicast
  Additional Paths receive capability: received
  Session: 172.31.255.3
  BGP table version 1, neighbor version 1/0
  Output queue size : 0
  Index 3, Advertise bit 0
  3 update-group member
  Slow-peer detection is disabled
  Slow-peer split-update-group dynamic is disabled
                                 Sent       Rcvd
  Prefix activity:               ----       ----
    Prefixes Current:               0          0
    Prefixes Total:                 0          0
    Implicit Withdraw:              0          0
    Explicit Withdraw:              0          0
    Used as bestpath:             n/a          0
    Used as multipath:            n/a          0
    Used as secondary:            n/a          0

                                   Outbound    Inbound
  Local Policy Denied Prefixes:    --------    -------
    Total:                                0          0
  Number of NLRIs in the update sent: max 0, min 0
  Last detected as dynamic slow peer: never
  Dynamic slow peer recovered: never
  Refresh Epoch: 1
  Last Sent Refresh Start-of-rib: never
  Last Sent Refresh End-of-rib: never
  Last Received Refresh Start-of-rib: never
  Last Received Refresh End-of-rib: never
				       Sent	  Rcvd
	Refresh activity:	       ----	  ----
	  Refresh Start-of-RIB          0          0
	  Refresh End-of-RIB            0          0

  Address tracking is enabled, the RIB does have a route to 172.31.255.3
  Route to peer address reachability Up: 1; Down: 0
    Last notification 00:23:02
  Connections established 3; dropped 2
  Last reset 00:07:58, due to BGP Notification received of session 1, Administrative Reset
  External BGP neighbor may be up to 2 hops away.
  External BGP neighbor NOT configured for connected checks (multi-hop no-disable-connected-check)
  Interface associated: (none) (peering address NOT in same link)
  Transport(tcp) path-mtu-discovery is enabled
  Graceful-Restart is disabled
  SSO is disabled
Connection state is ESTAB, I/O status: 1, unread input bytes: 0
Connection is ECN Disabled, Mininum incoming TTL 0, Outgoing TTL 2  <<<< Outgoing TTL value change to 2
Local host: 172.31.255.2, Local port: 179
Foreign host: 172.31.255.3, Foreign port: 40341
Connection tableid (VRF): 0
Maximum output segment queue size: 50

Enqueued packets for retransmit: 0, input: 0  mis-ordered: 0 (0 bytes)

Event Timers (current time is 0x21AF02):
Timer          Starts    Wakeups            Next
Retrans            13          0             0x0
TimeWait            0          0             0x0
AckHold            12         11             0x0
SendWnd             0          0             0x0
KeepAlive           0          0             0x0
GiveUp              0          0             0x0
PmtuAger            0          0             0x0
DeadWait            0          0             0x0
Linger              0          0             0x0
ProcessQ            0          0             0x0

iss: 3711084118  snduna: 3711084389  sndnxt: 3711084389
irs:  120895705  rcvnxt:  120895972

sndwnd:  15790  scale:      0  maxrcvwnd:  16384
rcvwnd:  16118  scale:      0  delrcvwnd:    266

SRTT: 824 ms, RTTO: 2094 ms, RTV: 1270 ms, KRTT: 0 ms
minRTT: 2 ms, maxRTT: 1000 ms, ACK hold: 120 ms
uptime: 477616 ms, Sent idletime: 1903 ms, Receive idletime: 2024 ms
Status Flags: passive open, gen tcbs
Option Flags: nagle, path mtu capable, SACK option permitted
  win-scale
IP Precedence value : 6
Window update Optimisation : Enabled
ACK Optimisation : Dynamic ACK Tuning Enabled

Datagrams (max data segment is 1460 bytes):
Peer MSS:       1460
Rcvd: 26 (out of order: 0), with data: 12, total data bytes: 266
Sent: 25 (retransmit: 0, fastretransmit: 0, partialack: 0, Second Congestion: 0), with data: 12, total data bytes: 270

 Packets received in fast path: 0, fast processed: 0, slow path: 0
 fast lock acquisition failures: 0, slow path: 0
TCP Semaphore      0x7FFFDCEA4B70  FREE
```

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/ebgp-multihop-ttl.png)


---

### `ttl-security` (GTSM)

Standardized as **GTSM — Generalized TTL Security Mechanism (RFC 5082)**. Protects eBGP sessions by checking incoming TTL against a threshold, instead of just checking for one decrement.

```cisco
neighbor <ip> ttl-security hops <N>
```

- Router expects incoming TTL ≥ `255 − N`.
- Packets below that threshold are silently discarded.
- Works because a legitimate peer within `N` hops still arrives with a high TTL; a spoofed packet injected from farther away arrives with a lower TTL and gets rejected — even with a faked source IP.

> ⚠️ **Exception / Rule:** `ebgp-multihop` and `ttl-security` are **mutually exclusive** on most platforms (Cisco, Juniper). Configure one or the other per session — never both.

#### sample output of ttl-security

```log
iol1#sh run | sec bgp

router bgp 131074
 bgp router-id 172.31.255.2
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 172.31.255.3 remote-as 196611
 neighbor 172.31.255.3 ttl-security hops 2
 neighbor 172.31.255.3 update-source Loopback0
 !
 address-family ipv4
  neighbor 172.31.255.3 activate
 exit-address-family
```

```log
iol1#show ip bgp neighbors 172.31.255.3
BGP neighbor is 172.31.255.3,  remote AS 196611, external link
  BGP version 4, remote router ID 172.31.255.3
  BGP state = Established, up for 00:03:55
  Last read 00:00:40, last write 00:00:28, hold time is 180, keepalive interval is 60 seconds
  Last update received: never
  Neighbor sessions:
    1 active, is not multisession capable (disabled)
  Neighbor capabilities:
    Route refresh: advertised and received(new)
    Four-octets ASN Capability: advertised and received
    Address family IPv4 Unicast: advertised and received
    Graceful Restart Capability: received
      Remote Restart timer is 300 seconds
      N bit (graceful-restart extended): received
      Address families advertised by peer:
        none
      Address families advertised by peer before restart:
        none
    Enhanced Refresh Capability: advertised and received
    Multisession Capability:
    Stateful switchover support enabled: NO for session 1
  Message statistics:
    InQ depth is 0
    OutQ depth is 0

                         Sent       Rcvd
    Opens:                  1          1
    Notifications:          0          0
    Updates:                1          0
    Keepalives:             6          6
    Route Refresh:          0          0
    Total:                  8          7
  Do log neighbor state changes (via global configuration)
  Default minimum time between advertisement runs is 30 seconds

 For address family: IPv4 Unicast
  Additional Paths receive capability: received
  Session: 172.31.255.3
  BGP table version 1, neighbor version 1/0
  Output queue size : 0
  Index 7, Advertise bit 0
  7 update-group member
  Slow-peer detection is disabled
  Slow-peer split-update-group dynamic is disabled
                                 Sent       Rcvd
  Prefix activity:               ----       ----
    Prefixes Current:               0          0
    Prefixes Total:                 0          0
    Implicit Withdraw:              0          0
    Explicit Withdraw:              0          0
    Used as bestpath:             n/a          0
    Used as multipath:            n/a          0
    Used as secondary:            n/a          0

                                   Outbound    Inbound
  Local Policy Denied Prefixes:    --------    -------
    Total:                                0          0
  Number of NLRIs in the update sent: max 0, min 0
  Last detected as dynamic slow peer: never
  Dynamic slow peer recovered: never
  Refresh Epoch: 1
  Last Sent Refresh Start-of-rib: never
  Last Sent Refresh End-of-rib: never
  Last Received Refresh Start-of-rib: never
  Last Received Refresh End-of-rib: never
				       Sent	  Rcvd
	Refresh activity:	       ----	  ----
	  Refresh Start-of-RIB          0          0
	  Refresh End-of-RIB            0          0

  Address tracking is enabled, the RIB does have a route to 172.31.255.3
  Route to peer address reachability Up: 1; Down: 0
    Last notification 01:03:24
  Connections established 7; dropped 6
  Last reset 00:03:57, due to BGP Notification received of session 1, Administrative Reset
  External BGP neighbor may be up to 2 hops away.
  External BGP neighbor NOT configured for connected checks (multi-hop no-disable-connected-check)
  Interface associated: (none) (peering address NOT in same link)
  Transport(tcp) path-mtu-discovery is enabled
  Graceful-Restart is disabled
  SSO is disabled
Connection state is ESTAB, I/O status: 1, unread input bytes: 0
Connection is ECN Disabled, Mininum incoming TTL 253, Outgoing TTL 255  <<<< During this ttl-security enable the bgp ttl will set to 255
Local host: 172.31.255.2, Local port: 179
Foreign host: 172.31.255.3, Foreign port: 43097
Connection tableid (VRF): 0
Maximum output segment queue size: 50

Enqueued packets for retransmit: 0, input: 0  mis-ordered: 0 (0 bytes)

Event Timers (current time is 0x46A11E):
Timer          Starts    Wakeups            Next
Retrans             8          0             0x0
TimeWait            0          0             0x0
AckHold             7          5             0x0
SendWnd             0          0             0x0
KeepAlive           0          0             0x0
GiveUp              0          0             0x0
PmtuAger            0          0             0x0
DeadWait            0          0             0x0
Linger              0          0             0x0
ProcessQ            0          0             0x0

iss:  778244997  snduna:  778245192  sndnxt:  778245192
irs:   40263074  rcvnxt:   40263246

sndwnd:  15866  scale:      0  maxrcvwnd:  16384
rcvwnd:  16213  scale:      0  delrcvwnd:    171

SRTT: 656 ms, RTTO: 2806 ms, RTV: 2150 ms, KRTT: 0 ms
minRTT: 1 ms, maxRTT: 1000 ms, ACK hold: 120 ms
uptime: 235862 ms, Sent idletime: 28687 ms, Receive idletime: 28684 ms
Status Flags: passive open, gen tcbs
Option Flags: nagle, path mtu capable, SACK option permitted
  win-scale
IP Precedence value : 6
Window update Optimisation : Enabled
ACK Optimisation : Dynamic ACK Tuning Enabled

Datagrams (max data segment is 1460 bytes):
Peer MSS:       1460
Rcvd: 15 (out of order: 0), with data: 7, total data bytes: 171
Sent: 15 (retransmit: 0, fastretransmit: 0, partialack: 0, Second Congestion: 0), with data: 8, total data bytes: 194

 Packets received in fast path: 0, fast processed: 0, slow path: 0
 fast lock acquisition failures: 0, slow path: 0
TCP Semaphore      0x7FFFDDE6F1C0  FREE
```

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/ttl-security.png)


---

### Quick Comparison

| | `ebgp-multihop` | `ttl-security` (GTSM) |
|---|---|---|
| Purpose | Enables multihop reachability | Protects against spoofing |
| TTL behavior | Increases outgoing TTL | Checks incoming TTL ≥ threshold |
| Security benefit | None on its own | Yes |
| Typical use | Loopback peering, redundant paths | Any eBGP session needing spoofing protection |

> 📝 **Rule of thumb:** iBGP sessions don't usually need `ttl-security` — they're within a trusted AS and already default to TTL 255.