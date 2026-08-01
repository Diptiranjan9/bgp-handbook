## BGP Aggregation (Route Summarization)

> 💡 **TL;DR:** BGP aggregation lets you announce one summary prefix (e.g., `160.0.0.0/8`) instead of many specific ones, shrinking the global routing table and improving stability — a flapping /24 no longer forces a withdrawal update across the internet if the aggregate stays up. The `aggregate-address` command has several optional keywords (`summary-only`, `as-set`, `suppress-map`, `advertise-map`, `attribute-map`) that control exactly which components get summarized, whether they're still advertised individually, and what attributes the resulting aggregate carries.

Related: [[BGP Path Selection]] · [[BGP Attributes]] · [[Traffic Engineering with AS_PATH]] · [[BGP Community]]

References: [Cisco — Understand Route Aggregation in BGP](https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/5441-aggregation.html) · [Noction — BGP Route Aggregation](https://www.noction.com/knowledge-base/bgp-route-aggregation)

---

### What is BGP Aggregation?

- Also called **Route Summarization** — replaces multiple specific prefixes with one shorter, less-specific prefix before advertising it to peers.
- Opposite of announcing every individual sub-prefix received from an RIR block.

**Why it matters:**
| Benefit | Why |
|---|---|
| Smaller routing table | Fewer entries stored in the global BGP table and router's FIB/TCAM |
| Less router workload | Fewer prefixes to process, compare, and forward |
| Saves bandwidth | Fewer UPDATE messages exchanged |
| **Routing stability** | A flapping /24 component doesn't force a withdrawal of the aggregate — as long as at least one component stays reachable, the aggregate keeps being advertised, so upstream routers never see the flap |

> 📝 **Real-world example:** An AS announcing 16 individual /24s can often be reduced to a single /20 — a ~94% reduction in advertised prefixes for that block, cutting FIB/TCAM load across every router carrying the full table.

---

### Component Routes

- The specific, more-detailed prefixes that make up an aggregate are called **component routes** (or contributors).
- A component route can enter the BGP table via:
  - The `network` statement
  - Redistribution from an IGP
  - Learning it from another BGP peer

> ⚠️ **Gotcha:** An aggregate is only advertised to a neighbor **as long as at least one component route exists** in the BGP table. If all components disappear, the aggregate is withdrawn too — aggregation hides flapping, it doesn't create a phantom route with nothing behind it.

---

### `aggregate-address` — Base Syntax

```cisco
aggregate-address <address> <mask> [as-set] [summary-only] [suppress-map <map>] [advertise-map <map>] [attribute-map <map>]
```

> ⚠️ **Gotcha:** Used with no keywords at all, `aggregate-address` creates the aggregate **and still advertises every component route alongside it** — nothing is suppressed by default, and the aggregate does **not** inherit AS_PATH/community from the components unless `as-set` is used.

---

### Option: `summary-only`

- Advertises **only** the aggregate — suppresses all component routes from being advertised individually.
- Component routes still show in the local BGP table marked `s>` (suppressed) — they're just not sent to peers.

```cisco
router bgp 3695
 network 70.36.0.0 mask 255.255.255.0
 aggregate-address 70.36.0.0 255.255.240.0 summary-only
 neighbor 12.0.0.2 remote-as 11260
```

---

### Option: `as-set`

- Without `as-set`, the aggregate is advertised with **no AS_PATH info** from the components — origin appears to be your own AS with no history of where the components actually came from.
- With `as-set`, the aggregate's AS_PATH becomes a **set** (unordered list, shown in `{}`) of every AS the component routes passed through — e.g., `300 {200,100}`.

```cisco
aggregate-address 160.0.0.0 255.0.0.0 summary-only as-set
```

> ⚠️ **Critical use — loop prevention:** The AS_SET is what lets BGP's loop detection work correctly for aggregates. If the aggregate update ever propagates back to an AS listed in the AS_SET, that router sees its **own AS** inside the set and **drops the route** — preventing a loop that would otherwise be invisible (since aggregation by default strips AS_PATH history).

> ⚠️ **Trade-off:** With `as-set`, if any one component route flaps, the AS_SET recalculates and the aggregate itself sends an update — meaning **many flapping components can cause the aggregate to flap too**, partially undermining the stability benefit of aggregation. This is a real operational trade-off to weigh.

---

### Option: `suppress-map`

- Selectively suppresses **specific** component routes (matched via a route-map/prefix-list) instead of suppressing all of them like `summary-only` does.
- Routes **not** matched by the suppress-map continue to be advertised alongside the aggregate.

```cisco
ip prefix-list my_sup_list seq 10 permit 70.36.0.0/24
!
route-map my_sup_map permit 10
 match ip address prefix-list my_sup_list
!
aggregate-address 70.36.0.0 255.255.240.0 suppress-map my_sup_map
```

> 📝 **Note:** If `suppress-map` is combined with `summary-only`, `summary-only` becomes redundant — `suppress-map`'s selective suppression takes over as the effective behavior.

---

### Option: `unsuppress-map`

- Re-enables advertisement of a specific suppressed component route, but **on a per-neighbor basis** — lets you show a specific neighbor a more-specific route while everyone else only sees the aggregate.

```cisco
aggregate-address 70.36.0.0 255.255.240.0 summary-only
neighbor 12.0.0.2 unsuppress-map my_unsup_map
!
ip prefix-list my_unsup_list seq 10 permit 70.36.1.0/24
route-map my_unsup_map permit 10
 match ip address prefix-list my_unsup_list
```

---

### Option: `attribute-map`

- Overrides specific attributes (community, MED, origin, etc.) on the **aggregate itself**, regardless of what the components carried.
- Commonly used to strip an unwanted inherited community (e.g., turn `no-export` into `none` so the aggregate can actually leave the AS).

```cisco
aggregate-address 160.0.0.0 255.0.0.0 as-set summary-only attribute-map Map
!
route-map Map permit 10
 set community none
```

> ⚠️ **Gotcha (from Cisco's lab):** If even one component route carries `no-export`, and `as-set` is used without an `attribute-map` override, the **entire aggregate inherits `no-export`** and silently stops being advertised to eBGP peers — a classic "why did my aggregate disappear" troubleshooting scenario.

---

### Option: `advertise-map`

- Restricts which component routes contribute their attributes (especially AS_PATH, for the AS_SET) to the aggregate — only routes matched by the advertise-map are used to build the aggregate's inherited attributes.
- Unmatched components are excluded from the aggregate's AS_SET/attribute inheritance, even if they're still valid components.

```cisco
aggregate-address 160.0.0.0 255.0.0.0 as-set summary-only advertise-map SELECT_SP_ROUTE
!
access-list 1 permit 160.10.0.0 0.0.255.255
route-map SELECT_SP_ROUTE permit 10
 match ip address 1
```

---

### Interaction Summary (Order of Precedence)

| Combination | Behavior |
|---|---|
| `as-set` alone | Aggregate inherits AS_SET/attributes from **all** components (suppressed or not) |
| `as-set` + `suppress-map` | Suppressed routes aren't advertised, but **still contribute** their attributes to the aggregate's AS_SET |
| `as-set` + `suppress-map` + `advertise-map` | Aggregate inherits attributes **only** from routes selected in `advertise-map` — `suppress-map` selection is irrelevant to attribute inheritance once `advertise-map` is present |
| `advertise-map` + `attribute-map` | `attribute-map` **overrides** whatever `advertise-map` selected — final word always goes to `attribute-map` |

> 📝 **Rule of thumb:** If `advertise-map` is configured, it alone decides what the aggregate inherits. Without it, the aggregate inherits from all components (suppressed + unsuppressed). In either case, `attribute-map` can override the result afterward.

---

### Static Discard Route (Legacy Method)

An older/alternative approach: create a static discard route to `Null0` matching the aggregate block, then use a plain `network` statement (with the aggregate mask) to inject it into BGP — no `aggregate-address` command needed.

```cisco
network 70.36.0.0 mask 255.255.240.0
!
ip route 70.36.0.0 255.255.240.0 Null0
```

- Traffic matching the aggregate but with **no more-specific route** gets discarded (prevents routing loops back toward the advertising router for addresses that aren't actually assigned yet).
- Still used in some designs, but `aggregate-address` is the more flexible, BGP-native mechanism.

---

## Traffic Engineering with Aggregation

Aggregation itself is primarily a **scaling and stability tool**, not a TE tool — but it interacts with TE in a few important ways, and can be *used* for TE-adjacent purposes:

### 1. Aggregation Can Undermine Your Existing TE
> ⚠️ **Gotcha:** If you've carefully set LOCAL_PREF, MED, or AS_PATH prepending on specific component prefixes, and then aggregate them **without `as-set` or `attribute-map`**, the aggregate route **loses all of that per-prefix attribute granularity** — every downstream router just sees one flat aggregate with default/local attributes. Always pair TE policy with `as-set` + `attribute-map` if the components need to retain distinguishing attributes, or keep the TE'd prefixes **out** of the aggregate entirely (via `advertise-map` exclusion or simply not summarizing them).

### 2. Using `attribute-map` to Apply TE to the Whole Aggregate at Once
Instead of tagging dozens of components individually, set the community/MED/origin **once** on the aggregate:

```cisco
aggregate-address 160.0.0.0 255.0.0.0 as-set summary-only attribute-map Set_Attribute
!
route-map Set_Attribute permit 10
 set community 3695:500
```

This is a common way to apply a **community-based TE signal** (e.g., a custom community your upstream understands) to an entire aggregated block in one place, rather than repeating the same `set community` across every component route-map.

### 3. Selectively Excluding Prefixes from the Aggregate for Independent TE
Use `advertise-map` (to control AS_SET) combined with **simply not summarizing** certain prefixes, if a specific customer/prefix needs its own independent TE policy (its own LOCAL_PREF, prepending, MED) that shouldn't be flattened into the aggregate's shared behavior.

> 📝 **Pattern:** Keep prefixes that need **individual** TE control advertised separately (outside the aggregate), and only aggregate the "bulk" prefixes that share the same policy — this avoids the granularity loss described above while still getting the table-size benefit for the majority of your announced space.

### 4. Aggregation as an Availability/Stability TE Technique
- Since an aggregate stays up as long as **any one component** is reachable, aggregating a customer's multiple subnets means a single flapping link doesn't force global route withdrawal/re-announcement — indirectly this is a form of TE for **stability**, not path preference: it prevents unnecessary reconvergence events from rippling outward while a component briefly flaps.

---

### Quick Comparison — Aggregation vs Other TE Tools

| Tool | Primary Purpose | Effect on Route Table Size | Grants Per-Prefix Control? |
|---|---|---|---|
| LOCAL_PREF / MED / AS_PATH | Path preference (TE) | No effect | Yes — full granularity |
| BGP Community | Delegated TE signaling | No effect | Yes — full granularity |
| **Aggregation** | Table size reduction + stability | **Reduces significantly** | **No, by default** — needs `as-set`/`attribute-map` to retain any |

> 💡 **Bottom line:** Aggregation and TE aren't opposites, but they pull in different directions — TE wants granularity per prefix, aggregation wants to erase granularity for efficiency. Use `as-set`, `attribute-map`, and `advertise-map` deliberately whenever both are needed on the same block.