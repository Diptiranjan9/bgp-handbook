#!/usr/bin/bash
ip addr add 172.16.1.2/24 dev eth1
ip link set dev eth1 mtu 1500
ip route replace default via 172.16.1.1

#python3 -c 'from scapy.all import *; send(IP(src="172.16.1.2", dst="10.10.10.10")/TCP(dport=8000, flags="F"))'

#TCP Flood
#scapy
#pkt = IP(src="172.16.1.2", dst="10.10.10.10") / TCP(dport=8000, flags="S")
#send(pkt, loop=1, inter=0.1)
#python3 -c 'from scapy.all import *; send(IP(src="172.16.1.2", dst="10.10.10.10")/TCP(dport=8000, flags="S")/Raw(load="X"*46), count=5)'

#UDP Flood
#scapy
#pkt = IP(dst="10.10.10.10") / UDP(dport=53) / DNS(rd=1, qd=DNSQR(qname="ns1.eptstech.arpa")) / Raw(load="A"*620)
#send(pkt, loop=1, inter=0.05)  # Sends ~20 packets/sec

#dig @10.10.10.10 TXT google.com +bufsize=4096 +dnssec
