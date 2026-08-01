## BGP AS_PATH Regular Expressions — Cheat Sheet

> 💡 **TL;DR:** AS_PATH regex matching is how AS-path filter-lists decide which routes to permit/deny. The trickiest part isn't the regex syntax itself — it's understanding that `_` (underscore) is a special **AS-boundary token**, not a literal character, matching a space, comma, brace/paren, OR the start/end of the entire path. Getting that one symbol right resolves 90% of AS-path filtering confusion.

Related: [[Traffic Engineering with AS_PATH]] · [[BGP Filtering]] · [[BGP Path Selection]]

---

### AS_PATH Regex Symbols

| Symbol | Meaning |
|---|---|
| `^` | Beginning of the AS_PATH |
| `$` | End of the AS_PATH |
| `.` | Matches any single character |
| `*` | Zero or more occurrences of the preceding expression |
| `+` | One or more occurrences of the preceding expression |
| `?` | Zero or one occurrence of the preceding expression |
| `()` | Groups multiple expressions together |
| `[]` | Character class — matches any one character within the brackets |
| `_` | **AS boundary** — matches start-of-path, end-of-path, a space, a comma, or a brace/paren `{}()` |

> ⚠️ **Critical to understand `_` correctly:** It is NOT a literal space — it's a stand-in for "any valid AS separator, including the very start or end of the path." This is exactly why patterns like `^65001_` mean "starts with 65001" regardless of whether 65001 is the *only* AS in the path or the *first of several* — the boundary matches either a following space or the end of the string.

---

### Common Patterns

| Regex | Meaning | Example Match |
|---|---|---|
| `^$` | Locally originated route (empty AS_PATH) | *(empty)* |
| `^65001$` | Exactly AS 65001, alone | `65001` |
| `^65001_` | Starts with AS 65001 | `65001 100 200` |
| `_65001$` | Ends with AS 65001 (origin AS) | `100 200 65001` |
| `_65001_` | Contains AS 65001 anywhere | `100 65001 200` |
| `.*` | Matches every AS_PATH | Any path |
| `^.+$` | Any non-empty AS_PATH | `100`, `100 200` |
| `^[0-9]+_[0-9]+$` | Exactly two AS numbers | `100 200` |
| `^[0-9]+_[0-9]+_[0-9]+$` | Exactly three AS numbers | `100 200 300` |
| `_100_.*_200_` | Contains both AS 100 and AS 200 | `300 100 500 200` |
| `^(100\|200)_` | Starts with AS 100 or AS 200 | `100 300`, `200 400` |
| `_(100\|200)$` | Ends with AS 100 or AS 200 | `300 100`, `400 200` |
| `_(100\|200)_` | Contains AS 100 or AS 200 anywhere | `300 100 500`, `400 200 600` |

> ⚠️ **Correction — trailing-boundary patterns match "N or more," not "exactly N+1":**
> `^[0-9]+_[0-9]+_[0-9]+_` is often labeled "four or more AS numbers." That's **incorrect**. Because the final `_` can match the **end-of-path boundary** (not just a space before a 4th AS), this pattern actually matches AS_PATHs with **three or more** AS numbers — `100 200 300` alone satisfies it, since the trailing `_` is happy to match "end of string" with nothing further required.
>
> | Pattern | Correct Meaning |
> |---|---|
> | `^[0-9]+_[0-9]+_[0-9]+$` | **Exactly** three AS numbers (anchored with `$`) |
> | `^[0-9]+_[0-9]+_[0-9]+_` | **Three or more** AS numbers (no `$`, so trailing boundary can match a space + continue, or end) |
>
> 📝 **Rule of thumb:** If you want to match an **exact** AS count, always anchor with `$` at the end. Leaving off the `$` almost always means "this many or more," because `_` is flexible about what comes next.

---

### Typical Uses

| Goal | Pattern |
|---|---|
| Match local routes | `^$` |
| Match customer-originated routes | `^65001$` |
| Match all routes learned from a neighboring AS | `^65001_` |
| Match routes originated by a specific AS | `_65001$` |
| Block or prefer routes containing an AS | `_65001_` |
| Reject AS loops | `_<your-AS>_` |
| Match multiple providers | `^(100\|200)_` |

---

### Cisco IOS

```cisco
ip as-path access-list 10 permit ^$
ip as-path access-list 20 permit ^65010_
ip as-path access-list 30 permit _65020_
ip as-path access-list 40 deny _65030_
ip as-path access-list 50 permit .*
```

### Route-Map Usage

```cisco
route-map FILTER-IN permit 10
 match as-path 20

route-map FILTER-IN deny 20
 match as-path 40

route-map FILTER-IN permit 30
```

> 📝 **Note:** Route-map clauses are evaluated top-down, first match wins. Here, clause 10 permits anything matching AS-path list 20, clause 20 explicitly denies anything matching list 40 (even if it would've matched clause 10's criteria too — order matters), and clause 30 is a catch-all permit for everything else.

---

### Junos

```junos
policy-options {
    as-path LOCAL "^$";
    as-path ISP "^65010_";
    as-path BLOCK "_65030_";
}
```

### FRRouting

```frr
bgp as-path access-list CUSTOMER permit ^65010$
bgp as-path access-list ISP permit ^65020_
bgp as-path access-list BLOCK deny _65030_
```

---

### Top 10 Patterns to Memorize

1. `^$` — locally originated
2. `^65001$` — exactly this AS, alone
3. `^65001_` — starts with this AS
4. `_65001$` — originated by this AS (last in path)
5. `_65001_` — contains this AS anywhere
6. `^(100|200)_` — starts with either AS
7. `_(100|200)$` — ends with either AS
8. `_(100|200)_` — contains either AS anywhere
9. `.*` — match everything
10. `^[0-9]+_[0-9]+$` — exactly two AS numbers (anchored)

> 💡 **Testing tip:** Always verify a new AS-path filter with `show ip bgp regexp <pattern>` (Cisco/Arista) or `show route aspath-regex <pattern>` (Junos) **before** applying it to a live neighbor — regex edge cases (like the "N or more" gotcha above) are easy to get subtly wrong, and a bad AS-path filter can silently drop or leak far more than intended.

---

### Examples

```log
route-views>show ip bgp regexp _7018_7018_

BGP table version is 1284492961, local router ID is 128.223.51.103
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter,
              x best-external, a additional-path, c RIB-compressed,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
V*   69.161.205.0/24  202.232.0.2                            0 2497 7018 7018 64230 ?
V*                    64.71.137.241                          0 6939 7018 7018 64230 i
```

- To view bgp table for locally originate

```log
inet-ceos#show ip bgp regex ^$
BGP routing table information for VRF default
Router identifier 172.16.1.1, local AS number 65002
Route status codes: s - suppressed contributor, * - valid, > - active, E - ECMP head, e - ECMP
                    S - Stale, c - Contributing to ECMP, b - backup, L - labeled-unicast, q - Pending FIB install
                    % - Pending best path selection
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI Origin Validation codes: V - valid, I - invalid, U - unknown
AS Path Attributes: Or-ID - Originator ID, C-LST - Cluster List, LL Nexthop - Link Local Nexthop

          Network                Next Hop              Metric  AIGP       LocPref Weight  Path
 * >      172.16.1.0/24          -                     -       -          -       0       i
```


```log
ios-ed1#show ip bgp

BGP table version is 10, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>i  10.10.10.10/32   10.0.1.5                 0    120      0 65001 i
 *bi                   10.0.1.6                      120      0 65001 i
 *>i  11.11.11.11/32   10.0.1.5                 0    100      0 65001 i
 *bi                   10.0.1.6                      100      0 65001 i
 *bi  172.16.1.0/24    10.0.1.4                      120      0 65002 i
 *>                    10.0.4.2                      120      0 65002 i
```

```log
ios-ed1#show ip bgp reg ^65002$

BGP table version is 10, local router ID is 10.0.1.3
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal, 
              r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, 
              x best-external, a additional-path, c RIB-compressed, 
              t secondary path, L long-lived-stale,
Origin codes: i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *bi  172.16.1.0/24    10.0.1.4                      120      0 65002 i
 *>                    10.0.4.2                      120      0 65002 i
```

```log
junos-ed2> show route protocol bgp aspath-regex ^65002$     

inet.0: 27 destinations, 30 routes (27 active, 0 holddown, 0 hidden)
+ = Active Route, - = Last Active, * = Both

172.16.1.0/24      *[BGP/170] 00:37:32, localpref 120
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.4.6 via eth4
                    [BGP/170] 01:00:26, MED 0, localpref 120, from 10.0.1.1
                      AS path: 65002 I, validation-state: unverified
                    >  to 10.0.3.1 via eth2

inet6.0: 14 destinations, 15 routes (14 active, 0 holddown, 0 hidden)
```