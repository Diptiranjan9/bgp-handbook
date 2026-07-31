<div align="right">
  <h1><strong> BGP </strong></h1>
</div>

## Introduction to BGP

> 💡 **TL;DR:** BGP is the routing protocol that connects different Autonomous Systems (ASes) on the internet. It's a path vector protocol — it makes routing decisions based on prefix attributes (like AS_PATH), not link state or distance, and runs over TCP port 179.

---

### What is BGP?

**The Border Gateway Protocol (BGP) is an inter-Autonomous System routing protocol.**

The primary function of a BGP speaking system is to exchange network reachability information with other BGP systems. This information includes the list of Autonomous Systems (ASes) that the reachability information traverses. This is sufficient to construct a graph of AS-level connectivity, from which routing loops can be pruned and AS-level policy decisions can be enforced.

📄 Reference: [BGP RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.html)

---

### Key Characteristics

| Property | Detail |
|---|---|
| Standard | Open standards-based (RFC 4271) |
| Protocol Class | Path Vector Protocol |
| Routing Category | Exterior Gateway Protocol (EGP-class) — routes *between* ASes, not within one |
| Transport | TCP, port 179 |
| Decision Basis | Prefix attributes (not link cost/bandwidth) |

> ⚠️ **Clarification:** "Exterior Gateway Protocol" here refers to the *category* of routing protocols that operate between ASes (as opposed to an Interior Gateway Protocol like OSPF/EIGRP). It's easy to confuse this with **EGP**, an actual (obsolete) protocol from the 1980s that BGP replaced. BGP is *an* exterior gateway protocol, not *the* EGP protocol.

---

### Path Vector Behavior

- As a path vector protocol, BGP uses **prefix attributes** to make routing decisions — not raw link metrics like bandwidth or delay.
- These attributes apply **per prefix**, not per link — meaning the same neighbor/link can carry different decision outcomes for different prefixes depending on their individual attributes.
- The BGP Best Path Selection process evaluates these attributes in a defined order (AS_PATH length, ORIGIN, LOCAL_PREF, MED, etc.) until a tiebreaker is found.

> 📝 **Note:** The commonly cited **"13-step" Best Path algorithm** is Cisco's specific implementation of the BGP decision process — the official count and exact order can vary slightly by vendor (Cisco, Juniper, etc.), though the core attributes (AS_PATH, LOCAL_PREF, MED, ORIGIN, etc.) are consistent across implementations per the RFC.

---

### Neighbor Formation

- BGP neighbors ("peers") form a session over **TCP port 179**.
- Using TCP (rather than a custom transport) gives BGP reliable delivery, ordering, and flow control for free — no need to reinvent reliability logic in the protocol itself.