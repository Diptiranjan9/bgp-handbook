#!/bin/bash

CHECK_DOMAIN="anycast.eptstech.arpa"
EXPECTED_IP="10.10.10.10"
INTERFACE="any0"
ANYCAST_IP="10.10.10.10/32"
INTERVAL=3

is_advertised=true

echo "[$(date)] Starting Netlink-Native DNS Anycast Health Checker..."

while true; do
    # 1. Capture the entire multi-line output from dig
    REPLY=$(dig @127.0.0.1 ${CHECK_DOMAIN} +short +time=1 +tries=1 2>/dev/null)

    # 2. Use grep to see if our expected IP exists as an exact line match (-x)
    if echo "$REPLY" | grep -q -x "${EXPECTED_IP}"; then
        if [ "$is_advertised" = false ]; then
            echo "[$(date)] DNS Recovered. Restoring IP ${ANYCAST_IP} to ${INTERFACE}..."
            ip addr add ${ANYCAST_IP} dev ${INTERFACE}
            is_advertised=true
        fi
    else
        if [ "$is_advertised" = true ]; then
            echo "[$(date)] ALERT: DNS query missing target IP! Stripping ${ANYCAST_IP}..."
            ip addr del ${ANYCAST_IP} dev ${INTERFACE}
            is_advertised=false
        fi
    fi
    sleep ${INTERVAL}
done