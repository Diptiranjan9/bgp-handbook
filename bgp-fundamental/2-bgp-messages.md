### BGP Message Types

- [BGP Message Types](#bgp-message-types)
  - [BGP MESSAGE FORMAT](#bgp-message-format)
  - [BGP Open Msg](#bgp-open-msg)
  - [BGP Update Msg](#bgp-update-msg)
  - [BGP Notification Msg](#bgp-notification-msg)
  - [BGP Keepalive Msg](#bgp-keepalive-msg)
  - [BGP Route Refresh Msg](#bgp-route-refresh-msg)



---
- **Open** - used to exchnage capabilities information, timers, ASN, etc.
- **Keepalive** - used to maintain the TCP session and make sure its healthy
- **Update** - used to send NLRI attributes and preifx information
- **Notifications** - ERRORS
- **Route Refresh** - To exchange changes in NLRI without having to reset peerings
---

#### BGP MESSAGE FORMAT

- Header - Marker, Length, Type
- Length - Defines the length of the BGP message
- Type - What kind of BGP message is this? 

| Message Type | Type Code |
|--------------|----------:|
| BGP Open | 1 |
| BGP Update | 2 |
| BGP Notification | 3 |
| BGP Keepalive | 4 |
| BGP Route Refresh | 5 |

#### BGP Open Msg

- Contains Version, My AS, Hold Time, BGP Identifier, Optional Paramters
  - BGP Identifier - BGP Router ID (Manually Configured, Highest Active Loopback IP, Highest Physical Interface IP)

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-openmsg.png)


#### BGP Update Msg

- Withdrawn Routes Length
- Wtihdrawn Routes
- Total Path Attribute Length
- Path Attributes
- NLRI

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-updatemsg.png)

#### BGP Notification Msg

- Error Code
- Error Subcode
- Data

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-notificationmsg.png)

#### BGP Keepalive Msg

- BGP sends Keepalive messages every one-third of the negotiated Hold Timer. For example, with a Hold Timer of 180 seconds, a Keepalive is sent every 60 seconds. These Keepalive messages continue to be sent as long as the BGP session is established. If no Keepalive or Update message is received from the peer within 180 seconds, the BGP session is terminated.

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-keepmsg.png)

#### BGP Route Refresh Msg

![](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-refreshmsg.png)