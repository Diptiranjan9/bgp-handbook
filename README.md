<div align="right">
  <h1><strong> BGP </strong></h1>
</div>

# Introduction

**The Border Gateway Protocol (BGP) is an inter-Autonomous System routing protocol.**

The primary function of a BGP speaking system is to exchange network reachability information with other BGP systems.  This network reachability information includes information on the list of Autonomous Systems (ASes) that reachability information traverses. This information is sufficient for constructing a graph of AS connectivity for this reachability, from which routing loops may be pruned and, at the AS level, some policy decisions may be enforced.

- [BGP RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.html)
- Open Standards Based Protocol
- Path Vector Protocol
- Exterior Gateway Protocol
- As a path vector routing protocol we use prefix attributes to make routing decisions (13 core decisions)
  - The attributes apply to the prefix (per prefix) and not the links themselves
- Use TCP port 179 to form neighbor