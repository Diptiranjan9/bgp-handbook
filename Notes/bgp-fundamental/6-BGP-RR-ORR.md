## BGP Route Reflector (RR) (RFC 4456)

> 💡 **TL;DR:** Route Reflectors remove the need for iBGP full-mesh by letting a designated router "reflect" routes between clients. Client routes get reflected to everyone; non-client routes only get reflected to clients (since non-clients are already fully meshed with each other). Loop prevention uses ORIGINATOR_ID and CLUSTER_LIST.

---

### Why Route Reflectors?

**Problem:**
- iBGP follows the **Split-Horizon Rule** — routes learned from an iBGP peer are NOT advertised to another iBGP peer.
- As the network grows, maintaining a full mesh becomes operationally difficult.
- Full-mesh iBGP sessions required: **n(n−1)/2**

| Routers (n) | Sessions Required |
|---:|---:|
| 10 | 45 |
| 100 | 4,950 |

**Solution:** Use **Route Reflectors** (RFC 4456) to break the full-mesh requirement without breaking loop prevention.

---

### Route Reflector Components

| Term | Definition |
|---|---|
| **Route Reflector (RR)** | A router designated to reflect routes between iBGP peers |
| **RR Client** | A router configured as a Route Reflector Client |
| **Non-Client** | A normal iBGP peer of the RR, not configured as a client |

---

### Route Reflection Rules

**Rule 1 — Route received from a Client**
→ Advertise to: **all other Clients, all Non-Clients, and eBGP peers**

**Topology:**
```text
Client-A ---- RR ---- Client-B
Client-A advertises 10.1.1.0/24
RR reflects to Client-B
```

**Rule 2 — Route received from a Client**
→ Advertise to: **Non-Clients**

**Topology:**
```text
Client-A ---- RR ---- Non-Client
Client-A advertises 10.1.1.0/24
RR reflects to Non-Client
```

**Rule 3 — Route received from a Non-Client**
→ Advertise to: **all Clients**

**Topology:**
```text
Non-Client ---- RR ---- Client-A
Non-Client advertises 10.1.1.0/24
RR reflects to Client-A
```

**Rule 4 — Route received from a Non-Client**
→ **NOT** advertised to other Non-Clients

**Topology:**
```text
Non-Client1 ---- RR ---- Non-Client2
Non-Client1 advertises 10.1.1.0/24
RR does NOT reflect to Non-Client2
```

> 📝 **Why Rule 4 exists:** Non-clients are assumed to already be part of a full iBGP mesh with each other (that's the whole point of being a "non-client" — normal iBGP peers). So Non-Client2 would learn the route directly from Non-Client1 anyway; reflecting it again would be redundant and risk a loop.

---

### Quick Reference Table

| Route Learned From | Reflected to Clients | Reflected to Non-Clients | Reflected to eBGP |
|---|:---:|:---:|:---:|
| Client | ✅ | ✅ | ✅ |
| Non-Client | ✅ | ❌ | ✅ |

---

### Route Reflector Loop Prevention

Route Reflectors intentionally break normal iBGP split-horizon behavior, so RFC 4456 defines two attributes to prevent loops instead:

> ⚠️ **Rule:** When a RR reflects a route, it **SHOULD NOT modify** NEXT_HOP, AS_PATH, LOCAL_PREF, or MED — modifying these could cause routing loops. ([RFC 4456 §10](https://www.rfc-editor.org/info/rfc4456/#section-10))

#### ORIGINATOR_ID
- Added by the RR when reflecting a route.
- Contains the **Router ID of the originating router**.
- If a router receives a route with its own Router ID as ORIGINATOR_ID, it **rejects** the route (it's the originator — this is its own route coming back).

#### CLUSTER_LIST
- Added by the RR when reflecting a route.
- Contains the list of **Cluster IDs** the route has traversed.
- If a router sees its **own Cluster ID** already in CLUSTER_LIST, it **rejects** the route.

---

### Interview Answer

> A Route Reflector removes the iBGP full-mesh requirement by reflecting routes between clients. Routes learned from a client are reflected to all other clients, non-clients, and eBGP peers. Routes learned from a non-client are reflected only to clients, not to other non-clients — since non-clients are expected to already be fully meshed with each other. Loop prevention is handled via ORIGINATOR_ID (rejects routes originated by yourself) and CLUSTER_LIST (rejects routes that already passed through your own cluster).

---

## BGP Optimal Route Reflection — BGP ORR (RFC 9107)

> 💡 **TL;DR:** Normally, a Route Reflector picks the best path based on its *own* IGP distance — not its clients'. BGP ORR fixes this by letting the RR calculate best path from the client's perspective instead, enabling proper "best exit point" / hot-potato routing even with centralized route reflectors.

### The Problem It Solves

- On a standard Route Reflector, BGP best-path selection is based on the **RR's own IGP location** — not the client's.
- In deployments with **centralized route reflectors** (RR physically/topologically far from its clients), this often leads to a **suboptimal exit point** for the client's traffic.

### The Solution

- BGP ORR modifies route selection **on the RR** to choose the best path **from the client's standpoint**, not the RR's own.
- Selection granularity is flexible:
  - Per single client
  - Per group of clients
  - Common for all clients of an RR
- Relies on the RR learning **all eligible paths** for a prefix (not just its own best path) and computing best path using **IGP cost from a configured reference location** in the link-state IGP — simulating "if I were sitting at the client's location, which path would I pick?"

> 📝 **Use case:** Enables **"best exit point" / hot-potato routing** — traffic exits the AS at the point closest to the client, rather than closest to a centralized RR.

**References:**
- [RFC 9107](https://datatracker.ietf.org/doc/rfc9107/)
- [Juniper: BGP Optimal Route Reflection](https://www.juniper.net/documentation/us/en/software/junos/bgp/topics/topic-map/bgp-optimal-route-reflection.html)

### Juniper Sample Output

```sh
root@junos-r2# show protocols        
bgp {
    group ibgp {
        type internal;
        local-address 100.64.0.2;
        cluster 100.64.0.2;
        local-as 100;
        optimal-route-reflection {
            igp-primary 100.64.0.1;
            igp-backup 100.64.0.4;
        }
        neighbor 100.64.0.1;
        neighbor 100.64.0.3;
        neighbor 100.64.0.4;
    }
    bgp-identifier 100.64.0.2;
}
```

```log
root@junos-r2> show bgp group detail ibgp 

Group Type: Internal    AS: 100                    Local AS: 100
  Name: ibgp            Index: 1                   Flags: <Export Eval>
  Options: <Cluster LocalAS>
  Options: <GracefulShutdownRcv>
  Holdtime: 90 Preference: 0
  Graceful Shutdown Receiver local-preference: 0
  Local AS: 100 Local System AS: 0
  Optimal route reflection: igp-primary 100.64.0.1 igp-backup 100.64.0.4
  Total peers: 3        Established: 3
  100.64.0.1+179
  100.64.0.3+179
  100.64.0.4+56379
  Route Queue Timer: unset Route Queue: empty
  Table inet.0
    Active prefixes:              1
    Received prefixes:            2
    Accepted prefixes:            2
    Suppressed due to damping:    0
    Advertised prefixes:          1
```

```log
root@junos-r2> show ospf bgp-orr 

Topology default Route Table:

BGP ORR Peer Group: ibgp
  Primary: 100.64.0.1, active
  Backup: 100.64.0.4
Prefix             Path  Route      Metric 
                   Type  Type
100.64.0.2         Intra Router          1
100.64.0.3         Intra Router          1
100.64.0.4         Intra Router          2
100.64.0.1/32      Intra Network         1
100.64.0.2/32      Intra Network         1
100.64.0.3/32      Intra Network         2
100.64.0.4/32      Intra Network         2
100.64.1.0/30      Intra Network         1
100.64.1.4/30      Intra Network         1
100.64.1.8/30      Intra Network         2
100.64.1.12/30     Intra Network         2
```