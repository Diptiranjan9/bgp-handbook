## BGP Message Types

> 💡 **TL;DR:** BGP has 5 message types — OPEN (capability exchange), KEEPALIVE (session health), UPDATE (route info), NOTIFICATION (errors), and ROUTE-REFRESH (soft reset). All share a common header (Marker, Length, Type) and ride over the same TCP 179 session.

---

### Message Types Overview

| Message | Purpose |
|---|---|
| **OPEN** | Exchange capabilities, timers, ASN, Router ID, etc. |
| **KEEPALIVE** | Maintain the TCP session and confirm it's healthy |
| **UPDATE** | Send NLRI, path attributes, and withdrawn prefix info |
| **NOTIFICATION** | Report errors and terminate the session |
| **ROUTE-REFRESH** | Request re-advertisement of NLRI without resetting the peering |

---

### BGP Message Format (Common Header)

Every BGP message shares a common header before its type-specific body:

| Field | Size | Purpose |
|---|---|---|
| Marker | 16 bytes | Historically for authentication; now typically all 1s (unused/legacy) |
| Length | 2 bytes | Total length of the BGP message (header + body) |
| Type | 1 byte | Identifies which of the 5 message types this is |

| Message Type | Type Code |
|---|---:|
| OPEN | 1 |
| UPDATE | 2 |
| NOTIFICATION | 3 |
| KEEPALIVE | 4 |
| ROUTE-REFRESH | 5 |

> 📝 **Note:** ROUTE-REFRESH (type 5) is an extension defined in RFC 2918 — the original RFC 4271 only defines types 1–4.

---

### OPEN Message

Fields: Version, My AS, Hold Time, BGP Identifier, Optional Parameters.

- **BGP Identifier** — the BGP Router ID, determined by (in order of precedence):
  1. Manually configured Router ID
  2. Highest IP among **active** loopback interfaces
  3. Highest IP among **active** physical interfaces

> ⚠️ **Gotcha:** The interface must be **active/up** to be considered — a configured-but-down loopback with a higher IP won't win Router ID selection.

![BGP Open Message](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-openmsg.png)

---

### UPDATE Message

Fields, in order:
1. Withdrawn Routes Length
2. Withdrawn Routes
3. Total Path Attribute Length
4. Path Attributes
5. NLRI

> 📝 **Note:** A single UPDATE message can carry withdrawals and new advertisements together, or just one of the two — it doesn't require both every time.

![BGP Update Message](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-updatemsg.png)

---

### NOTIFICATION Message

Fields: Error Code, Error Subcode, Data.

- Sent when BGP detects an error condition (e.g., malformed message, hold timer expiry, FSM error).
- **Terminates the session immediately** after being sent/received — this is what triggers the transition back to Idle in the BGP FSM.

![BGP Notification Message](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-notificationmsg.png)

---

### KEEPALIVE Message

- Sent every **1/3 of the negotiated Hold Timer**. Example: Hold Timer = 180s → KEEPALIVE sent every 60s.
- Continues for the life of the Established session.
- If no KEEPALIVE or UPDATE is received within the full Hold Timer (180s in this example), the session is **terminated**.

> 💡 **Tip:** Hold Timer and KEEPALIVE interval are negotiated during the OPEN exchange — both sides take the **lower** of their two configured Hold Timer values.

![BGP Keepalive Message](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-keepmsg.png)

---

### ROUTE-REFRESH Message

- Allows a router to request that a peer **re-send its full routing table** for a given AFI/SAFI, without tearing down the session.
- Requires the **Route Refresh capability** to be negotiated in the OPEN message.
- Common use case: applying a new inbound route-map/policy without a hard reset (`clear ip bgp * soft in` relies on this).

![BGP Route Refresh Message](https://github.com/Diptiranjan9/bgp-handbook/blob/main/snapshots/bgp-refreshmsg.png)