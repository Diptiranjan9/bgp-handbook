### USE CASE

- We use BGP to route between external ASs Internet
- Large Data Center Designs
- Scaling DMVPNs Locally Significant ASNs

### EXTENSIBILITY AND SCALABILITY

- AFIs (Address Family Identifiers)
- SAFIs (Sub AFIs)

### WHAT IS BGP?

- Not a routing protocol
- An application that runs on top of TCP designed to exchange NLRIs (port 179)
- BGP is a reachability protocol
- No transport protocol (e.g., OSPF uses IP protocol 89 and EIGRP uses IP protocol 88)

### IGP vS BGP (EGP)

- BGP has no visibility into the topology
- Routing from AS to AS

### PREFIX DESIGNATIONS

- Provider Assigned (PA)
  - ISP owns your address space
  - They dictate the policy
  - BGP most likely not needed

- Provider Independant (PI)
  - You own your address space
  - You dictate the policy
  - BGP is most likely needed
  - A lot of works