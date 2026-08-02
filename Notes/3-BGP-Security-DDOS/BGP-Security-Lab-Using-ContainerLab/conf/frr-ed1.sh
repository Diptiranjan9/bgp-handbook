#!/usr/bin/bash
ip link set dev eth1 mtu 1500
ip link set dev eth2 mtu 1500
ip link set dev eth3 mtu 1500
ip link set dev eth4 mtu 1500
ip link set dev eth5 mtu 1500
chmod +x /usr/local/bin/frr-flowspec-to-iptable.py
/usr/local/bin/frr-flowspec-to-iptable.py >/var/log/frr-flowspec-to-iptable.log 2>&1 &
sysctl -p /etc/sysctl.d/99-rpf.conf

#verification commands
#sysctl -a | grep rp_filter
#verification command in frr bash for ip table
#ipset list frr_ip_set
#iptables -t raw -L PREROUTING -v -n --line-numbers
#iptables -t raw -L BGP_FLOWSPEC -v -n --line-numbers
#watch -n 1 "iptables -t raw -L BGP_FLOWSPEC -v -n"