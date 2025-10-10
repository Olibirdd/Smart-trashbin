#!/bin/bash

# Usage: sudo ./whitelist_mac.sh AA:BB:CC:DD:EE:FF

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

MAC="$1"
IP="$2"

# if IP not given, try to discover from ARP
if [ -z "$IP" ]; then
    IP=$(ip neigh show dev enp2s0 | grep -i "$MAC" | awk '{print $1}')
fi


# Check if MAC is provided
if [ -z "$MAC" ]; then
    echo "Usage: $0 <MAC_ADDRESS>"
    exit 1
fi

# Validate MAC format (basic regex)
if [[ ! "$MAC" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
    echo "Error: Invalid MAC address format."
    exit 1
fi

# Ensure ipset exists
if ! ipset list hotlist &>/dev/null; then
    echo "hotlist ipset not found. Creating..."
    ipset create hotlist hash:mac
fi

# Check if MAC is already whitelisted
if ipset test hotlist "$MAC" &>/dev/null; then
    echo "MAC $MAC is already whitelisted."
else
    ipset add hotlist "$MAC"
    echo "MAC $MAC successfully whitelisted. "
fi


if [ -z "$IP" ]; then
    echo "Warning: Could not find IP for MAC $MAC. Client must be online and ARP entry must exist."
else
    # Add/update IP in ipset for Internet access
    if ! ipset test hotlist_ip "$IP" &>/dev/null; then
        ipset add hotlist_ip "$IP"
        echo "IP $IP added to hotlist_ip for Internet access"
    fi

    # Add/update IP in Nginx whitelist map
    MAPFILE=/etc/nginx/whitelist.map
    grep -v "^$IP " $MAPFILE > ${MAPFILE}.tmp 2>/dev/null
    echo "$IP 1;" >> ${MAPFILE}.tmp
    mv ${MAPFILE}.tmp $MAPFILE

    # Reload Nginx
    nginx -s reload
    echo "Whitelisted IP $IP added to Nginx. Captive portal banner should clear automatically."
fi


# Optional: show current whitelist
echo "Current whitelisted MACs:"
ipset list hotlist | grep -E "^[0-9A-Fa-f]"


