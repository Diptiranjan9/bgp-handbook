## iBGP vs eBGP

> 💡 **TL;DR:** eBGP connects different ASes and uses AS_PATH to prevent loops; iBGP stays within one AS and uses the split-horizon rule instead — which is why iBGP needs full mesh, Route Reflectors, or Confederations to scale.

Related: [[BGP TTL & Security Mechanisms]]

---

### Comparison Table

| Feature | iBGP | eBGP |
|---|---|---|
| AS Number | Same AS | Different AS |
| Administrative Distance (Cisco) | 200 | 20 |
| Default TTL | 255 | 1 |
| AS_PATH Modification | No | Prepends local AS |
| NEXT_HOP | Preserved by default | Usually changed to self |
| Loop Prevention | Split-Horizon Rule | AS_PATH Check |
| Peering Requirement | Full mesh / Route Reflector / Confederation | Typically direct link (or `ebgp-multihop`) |

---

### eBGP Loop Prevention

- **Mechanism:** AS_PATH
- **Rule:** A router rejects a route if its own AS number already appears in AS_PATH.

**Topology:**
```text
AS65001 → AS65002 → AS65003
Route returns with AS_PATH = 65001 65002 65003
AS65001 sees its own AS in AS_PATH → rejects the route
```

---

### iBGP Loop Prevention

- **Mechanism:** iBGP Split-Horizon
- **Rule:** Routes learned from an iBGP peer must NOT be advertised to another iBGP peer.

**Topology:**
```text
R1 ---iBGP--- R2 ---iBGP--- R3
R2 learns a route from R1 → cannot advertise it to R3
```

**Result:** Requires Full Mesh, Route Reflectors, or Confederations to propagate routes across all iBGP routers.

> ⚠️ **Exception:** Route Reflectors are specifically designed to bypass this rule in a controlled way — a Route Reflector *can* re-advertise a route learned from one iBGP client to another iBGP client. This is what allows networks to avoid full-mesh iBGP at scale.

---

### Route Advertisement Rules

**eBGP Learned → iBGP**

| Attribute | Behavior |
|---|---|
| AS_PATH | Unchanged |
| NEXT_HOP | Unchanged |

**Topology:**
```text
ISP ---eBGP--- R1 ---iBGP--- R2
R2 receives prefix 8.8.8.0/24 with NEXT_HOP = ISP
```

```cisco
neighbor X.X.X.X next-hop-self
```

> ⚠️ **Gotcha:** If R2 has no route to reach the ISP's next-hop IP directly, the prefix becomes unreachable until `next-hop-self` is applied on R1. This is one of the most common real-world iBGP misconfigurations.

---

**iBGP Learned → iBGP**

**Topology:**
```text
R1 ---iBGP--- R2 ---iBGP--- R3
R2 learns a route from R1 → cannot advertise it to R3
```

**Reason:** iBGP Split-Horizon Rule (unless R2 is a Route Reflector for R1/R3, or all three are full-meshed).

---

**iBGP Learned → eBGP**

**Topology:**
```text
R1 ---iBGP--- R2 ---eBGP--- ISP
R2 learns a route from R1 → advertises it to ISP
```

| Attribute | Behavior |
|---|---|
| AS_PATH | Local AS prepended |
| NEXT_HOP | Becomes R2 |