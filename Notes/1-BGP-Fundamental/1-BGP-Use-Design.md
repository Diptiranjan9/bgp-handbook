## BGP Use Cases, Design & Prefix Types

> 💡 **TL;DR:** BGP is used to route between ASes on the internet, in large DC fabrics, and to scale DMVPN with locally significant ASNs. It's technically an application-layer reachability protocol over TCP (not a classic IGP), and whether you need it often comes down to whether you own your IP space (PI) or lease it from your ISP (PA).


---

### Use Cases

- Routing between external ASes on the **Internet**
- **Large Data Center designs** (e.g., BGP in Clos/spine-leaf fabrics, often preferred over IGPs for scale and deterministic path control)
- **Scaling DMVPN** using **locally significant ASNs** (private ASNs reused per site/spoke, since BGP peering there doesn't need globally unique AS numbers)

---

### Extensibility & Scalability

BGP scales across many use cases (IPv4, IPv6, VPNs, multicast, etc.) through:

- **AFI** — Address Family Identifier (e.g., IPv4, IPv6)
- **SAFI** — Subsequent Address Family Identifier (e.g., unicast, multicast, MPLS VPN)

> 📝 **Note:** AFI/SAFI combinations are what let a single BGP session carry multiple types of routing information (e.g., IPv4 unicast + VPNv4) — this is the foundation of MP-BGP (Multiprotocol BGP).

---

### What is BGP, really?

- **Not a traditional IGP-style routing protocol** — it doesn't calculate best paths using link metrics like bandwidth, delay, or cost. It's better described as a **reachability protocol**: it tells you *what* is reachable and *via which AS path/attributes*, not the "shortest" path in a metric sense.
- BGP is an **application-layer process that runs on top of TCP** (port 179) to exchange **NLRIs** (Network Layer Reachability Information).
- Unlike OSPF and EIGRP, **BGP has no protocol of its own at the network layer** — it relies entirely on TCP for reliability, ordering, and delivery.

| Protocol | Runs Over |
|---|---|
| OSPF | IP Protocol 89 (directly over IP) |
| EIGRP | IP Protocol 88 (directly over IP) |
| BGP | TCP Port 179 (application layer, over IP) |

> ⚠️ **Clarification:** Saying "BGP is not a routing protocol" is a conceptual point, not literal — BGP absolutely makes routing decisions and installs routes. The point is that its *mechanism* is closer to an application exchanging reachability data over TCP, rather than a protocol with its own network-layer transport and metric-based path computation like a classic IGP.

---

### IGP vs BGP (EGP)

| | IGP (OSPF/EIGRP) | BGP (EGP-class) |
|---|---|---|
| Topology Visibility | Full visibility into internal topology | **No visibility** into underlying topology |
| Scope | Within a single AS | Between ASes |
| Decision Basis | Metrics (cost, bandwidth, delay) | Path attributes (AS_PATH, LOCAL_PREF, etc.) |

> 📝 **Note:** Because BGP has no topology awareness, it can't automatically route around a physical failure the way an IGP with SPF can — it only reacts to reachability/attribute changes it's told about.

---

### Prefix Designations

**Provider Assigned (PA)**
- ISP owns the address space
- ISP dictates the routing policy
- BGP is most likely **not needed** — a static or default route to the ISP is usually sufficient

**Provider Independent (PI)**
- You own the address space (assigned directly by an RIR, not the ISP)
- You dictate the routing policy
- BGP is most likely **needed** — required to announce your own prefixes across multiple ISPs/paths
- Comes with more operational overhead: ASN registration, RPKI/ROA management, multihoming design, etc.

> ⚠️ **Gotcha:** PI space gives you independence from any single ISP (easy to multihome or switch providers without renumbering), but it requires you to run BGP and manage your own routing policy — which is real ongoing operational work, not a one-time setup.