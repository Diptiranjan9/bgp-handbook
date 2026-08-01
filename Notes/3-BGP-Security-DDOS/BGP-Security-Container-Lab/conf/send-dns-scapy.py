#!/usr/bin/env python3
import time
import sys
from scapy.all import IP, UDP, DNS, DNSQR, send

def send_dns_traffic(src_ip, dst_ip, count=50, interval=0.1):
    print(f"[*] Sending {count} DNS UDP packets from {src_ip} to {dst_ip}:53...")
    
    # Construct DNS query packet
    packet = IP(src=src_ip, dst=dst_ip) / UDP(sport=12345, dport=53) / DNS(rd=1, qd=DNSQR(qname="test.local"))
    
    for i in range(1, count + 1):
        send(packet, verbose=False)
        print(f"\rSent {i}/{count} packets", end="", flush=True)
        time.sleep(interval)
        
    print("\n[+] Traffic generation finished.")

if __name__ == "__main__":
    # Adjust source IP to match your FlowSpec rules (172.16.1.2 or 172.16.1.5)
    SOURCE_IP = "172.16.1.2"
    TARGET_IP = "10.10.10.10"
    
    if len(sys.argv) > 1:
        SOURCE_IP = sys.argv[1]
        
    send_dns_traffic(src_ip=SOURCE_IP, dst_ip=TARGET_IP, count=100, interval=0.05)