#!/usr/bin/bash
ip link add any0 type dummy
ip link set any0 up
ip addr add 10.10.10.10/32 dev any0
ip addr add 11.11.11.11/32 dev any0
ip addr add 10.0.5.2/30 dev eth1
ip link set dev eth1 mtu 1500
ip route replace default via 10.0.5.1
bird -f -c /etc/bird/bird.conf >/var/log/bird.log 2>&1 &
dnsmasq -C /etc/dnsmasq.conf >/var/log/dnsmasq.log 2>&1 &
chmod +x /usr/local/bin/dns-healthcheck.sh
/usr/local/bin/dns-healthcheck.sh >/var/log/dns-healthcheck.log 2>&1 &
python3 -m http.server -b 10.10.10.10 >/var/log/http-server.log 2>&1 &