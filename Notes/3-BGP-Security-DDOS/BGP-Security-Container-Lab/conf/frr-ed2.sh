#!/usr/bin/bash
ip link set dev eth1 mtu 1500
ip link set dev eth2 mtu 1500
ip link set dev eth3 mtu 1500
ip link set dev eth4 mtu 1500
ip link set dev eth5 mtu 1500
# chmod +x /usr/local/bin/sync_flowspec_ipt.py
# /usr/local/bin/sync_flowspec_ipt.py >/var/log/sync_flowspec_ipt.log 2>&1 &
chmod +x /usr/local/bin/frr_universal_flowspec.py
/usr/local/bin/frr_universal_flowspec.py >/var/log/frr_universal_flowspec.log 2>&1 &
sysctl -p /etc/sysctl.d/99-rpf.conf
#sysctl -a | grep rp_filter
#verification command in frr bash for ip table
#ipset list frr_ip_set
#iptables -t raw -L PREROUTING -v -n --line-numbers
#iptables -t raw -L BGP_FLOWSPEC -v -n --line-numbers
#watch -n 1 "iptables -t raw -L BGP_FLOWSPEC -v -n"