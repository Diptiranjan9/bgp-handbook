## BGP Use Cases, Design & Prefix Types

> 💡 **TL;DR:** BGP is the inter-AS routing protocol of the internet. It exchanges reachability information and path attributes over TCP port 179, and is also used in large data-center fabrics (RFC 7938, eBGP) and WAN overlays such as DMVPN. Whether you need BGP depends less on PA/PI labels than on whether you multihome or need a routing policy different from your provider's.

---

### 1. Use Cases

| Use case | Notes |
|---|---|
| **Internet (inter-AS)** | Core purpose of BGP: exchange reachability between ASes |
| **Large data centers** | RFC 7938 (Informational) describes eBGP as a stand-alone routing protocol for Clos fabrics; drivers are operational simplicity and stability |
| **DMVPN / WAN overlays** | eBGP or iBGP between hub and spokes (see section 5) |

---

### 2. Extensibility: AFI / SAFI (MP-BGP, RFC 4760)

- Base BGP-4 carries only IPv4 NLRI. RFC 4760 adds the multiprotocol attributes **MP_REACH_NLRI (type 14)** and **MP_UNREACH_NLRI (type 15)**.
- **AFI** (Address Family Identifier, 2 octets) + **SAFI** (Subsequent Address Family Identifier, 1 octet) together identify the network-layer protocol for the next hop and the semantics of the NLRI.
- This is how BGP carries IPv6, L3VPN and other address families.

---

### 3. What BGP Is (and Isn't)

- RFC 4271 defines BGP as an **inter-Autonomous System routing protocol** that exchanges network reachability information, including the list of ASes traversed.
- Teaching shorthand: BGP is a *reachability protocol* that runs over TCP and does not compute link-state shortest paths.
- BGP uses **TCP port 179**, so TCP provides reliability, ordering and retransmission.

| Protocol | Runs over |
|---|---|
| OSPF | IP protocol 89 (RFC 2328) |
| EIGRP | IP protocol 88 (RFC 7868, Informational) |
| BGP | TCP port 179 |

> ⚠️ **Gotcha:** "BGP is not a routing protocol" is shorthand, not RFC wording. BGP has its own Decision Process and installs routes; "application-layer" is not RFC terminology either.

---

### 4. IGP vs BGP

| | IGP (OSPF/EIGRP) | BGP |
|---|---|---|
| Typical scope | Within one AS | Between ASes (eBGP); also inside an AS (iBGP) |
| Topology knowledge | Router/link-level topology | **AS-level** graph only |
| Decision basis | Metrics (cost, bandwidth, delay) | Path attributes first; **MED** and **IGP cost to the next hop** act as tie-breakers |
| Failure detection | Neighbor/SPF events | BGP session state (e.g. Hold Timer expiry); next hop must be resolvable via the routing table, so an IGP is still needed underneath |

> 📝 **Note:** BGP does not run SPF. It reacts to session loss and to updates and withdrawals it receives.

---

### 5. DMVPN with BGP: ASN Design

| Design | Behavior | Trade-off |
|---|---|---|
| **eBGP, unique private ASN per spoke** | eBGP loop prevention stays intact | 16-bit private range = 1,023 ASNs; the 32-bit private range (4200000000–4294967294) gives 94,967,295 |
| **eBGP, same ASN on all spokes** | Needs `allowas-in` on spokes, or `as-override` / `remove-private-as` on the hub | Weakens loop prevention; "dirty tricks" |
| **iBGP, hub as route reflector** | Same AS everywhere, spokes peer only with the hub | Needs route-reflector and next-hop handling |

> ⚠️ **Gotcha:** With the same ASN on every spoke, a spoke rejects other spokes' prefixes because its own ASN appears in the AS_PATH. This matters for spoke-to-spoke (phase 2) designs.

---

### 6. Prefix Designations: PA vs PI

PA/PI terminology comes from RIR address-policy documents, not from RFC 4271.

| | **Provider Assigned (PA)** | **Provider Independent (PI)** |
|---|---|---|
| Who holds the space | ISP | You (assigned via your RIR) |
| Routing policy | Follows the ISP's | You set it |
| BGP needed? | Usually not (static/default route to the ISP) | Usually yes, so every provider can announce your prefix |
| Renumbering when changing ISP | Yes | No |

**When is an AS (and therefore BGP with your own ASN) justified?** RFC 1930: only when your routing policy differs from that of your border peers. RFC 2270: organizations with the same policy as their upstream do not need an AS.

> ⚠️ **Gotcha:** PA vs PI is not the real test. Multihoming or a distinct routing policy is. PI makes that case common, and brings ongoing operational work (ASN registration through the RIR, prefix announcements, filtering).

---

### 7. CCIE-Depth: Maths, Corner Cases, Interactions

- **Private ASN capacity:** 64512–65534 = **1,023**; 4200000000–4294967294 = **94,967,295**.
- **eBGP loop prevention:** an update whose AS_PATH contains the receiver's own ASN is dropped. This is why shared-ASN designs (DMVPN spokes, data-center tiers) need extra configuration or careful ASN schemes.
- **RFC 7938 ASN schemes:** the RFC covers private-use ASNs and re-use of non-unique private ASNs in Clos fabrics.
- **Next-hop resolvability:** a BGP route is usable only if its next hop resolves in the routing table, which is why DC and WAN designs still run an underlay (IGP or connected/static routes).
- **16-bit ASN rules (RIPE example):** a 16-bit ASN needs a unique routing policy and multihoming within nine months of assignment; 32-bit ASNs are exempt. Other RIRs' rules differ.

---

### 8. Quick Recap

| Topic | Remember |
|---|---|
| BGP definition | Inter-AS routing protocol (RFC 4271), TCP 179 |
| Transport | TCP, unlike OSPF (IP 89) and EIGRP (IP 88) |
| Topology view | AS-level only |
| Decision basis | Attributes first; MED and IGP cost to next hop as tie-breakers |
| MP-BGP | AFI (2 octets) + SAFI (1 octet); attributes 14 and 15 |
| Data centers | RFC 7938: eBGP, simplicity and stability |
| DMVPN | Unique private ASN per spoke, or allowas-in/as-override, or iBGP + RR |
| Need an AS? | Only if your routing policy differs from your upstream's (RFC 1930) |
| PA vs PI | RIR terms; PI usually implies BGP |

---

### References

**Standards**
- [RFC 4271 — BGP-4](https://www.rfc-editor.org/rfc/rfc4271.html)
- [RFC 4760 — Multiprotocol Extensions for BGP-4](https://datatracker.ietf.org/doc/rfc4760)
- [RFC 7938 — Use of BGP for Routing in Large-Scale Data Centers](https://datatracker.ietf.org/doc/rfc7938/)
- [RFC 1930 — Guidelines for creation, selection, and registration of an AS](https://www.rfc-editor.org/rfc/rfc1930)
- [RFC 2270 — Using a Dedicated AS for Sites Homed to a Single Provider](https://www.rfc-editor.org/rfc/rfc2270)
- [RFC 6996 — AS Reservation for Private Use](https://www.rfc-editor.org/rfc/rfc6996)
- [RFC 2328 — OSPF Version 2](https://www.rfc-editor.org/rfc/rfc2328) · [RFC 7868 — EIGRP](https://www.rfc-editor.org/rfc/rfc7868)

**Vendor / community documentation**
- [ipSpace.net — Scaling BGP-Based DMVPN Networks](https://blog.ipspace.net/2014/03/scaling-bgp-based-dmvpn-networks/)
- [ipSpace.net — BGP Routing in DMVPN Access Network](https://www.ipspace.net/BGP_Routing_in_DMVPN_Access_Network)
- [Cumulus Linux — BGP](https://docs.cumulusnetworks.com/cumulus-linux-41/Layer-3/Border-Gateway-Protocol-BGP/)