#!/usr/bin/env python3
import time
import sys
import random
import socket
import struct
from scapy.all import IP, UDP, DNS, DNSQR, send, get_if_addr, conf

# ==================== CONFIGURATION ====================
TARGET_IP = "10.10.10.10"  # Target DNS Server / Router IP
TARGET_PORT = 53

# Delay between packets in seconds (0.05 = ~20 packets/sec)
DELAY = 0.05
# =======================================================

def get_legit_ip():
    """Auto-detects the host's primary local IP address."""
    try:
        return get_if_addr(conf.iface)
    except Exception:
        return "172.16.1.2"  # Fallback if interface detection fails

def generate_random_ip():
    """Generates a valid, random IPv4 address (skipping loopback, 0.x, multicast/reserved)."""
    while True:
        # Generate a random 32-bit integer converted to IPv4 format
        ip = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xFFFFFFFF)))
        
        # Filter out 0.0.0.0/8, 127.0.0.0/8 (loopback), and 224.0.0.0+ (multicast/reserved)
        first_octet = int(ip.split('.')[0])
        if not (first_octet == 0 or first_octet == 127 or first_octet >= 224):
            return ip

def start_traffic_generator(dst_ip, legit_src_ip):
    legit_count = 0
    spoofed_count = 0
    total_count = 0

    print("==========================================================")
    print("      SCAPY CONTINUOUS DNS TRAFFIC GENERATOR              ")
    print("==========================================================")
    print(f" Target Server    : {dst_ip}:{TARGET_PORT}")
    print(f" Legitimate IP    : {legit_src_ip}")
    print(f" Spoofed IPs      : Dynamic Random IPv4 per packet")
    print(f" Packet Delay     : {DELAY}s")
    print(" Press Ctrl+C to STOP the traffic generator.")
    print("==========================================================\n")

    try:
        while True:
            # 50% chance Legitimate IP, 50% chance Random Spoofed IP
            is_legit = random.choice([True, False])

            if is_legit:
                src_ip = legit_src_ip
                pkt_type = "LEGIT"
                legit_count += 1
            else:
                src_ip = generate_random_ip()
                pkt_type = "SPOOFED"
                spoofed_count += 1

            total_count += 1

            # Craft DNS Query Packet
            pkt = (
                IP(src=src_ip, dst=dst_ip) /
                UDP(sport=random.randint(1024, 65535), dport=TARGET_PORT) /
                DNS(rd=1, qd=DNSQR(qname="urpf-flowspec-test.lab"))
            )
            
            # Send packet silently (bypassing OS kernel IP checks)
            send(pkt, verbose=False)

            # Live updating stats output
            sys.stdout.write(
                f"\r[+] Total: {total_count} | Legit: {legit_count} | Spoofed: {spoofed_count} | Last: [{pkt_type}] {src_ip} -> {dst_ip}"
            )
            sys.stdout.flush()

            time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n\n[!] Traffic generator stopped by user.")
        print("----------------------------------------------------------")
        print(f" Final Summary: Sent {total_count} total packets ({legit_count} Legitimate, {spoofed_count} Spoofed).")
        print("----------------------------------------------------------")

if __name__ == "__main__":
    # Optional CLI overrides:
    # Usage: sudo python3 continuous_dns_test.py [LEGIT_SRC_IP] [TARGET_IP]
    my_legit_ip = sys.argv[1] if len(sys.argv) > 1 else get_legit_ip()
    my_target_ip = sys.argv[2] if len(sys.argv) > 2 else TARGET_IP

    start_traffic_generator(dst_ip=my_target_ip, legit_src_ip=my_legit_ip)