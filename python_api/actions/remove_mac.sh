#!/bin/bash
# Usage: sudo ./revoke_mac.sh <MAC_ADDRESS>

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

MAC="$1"

# Validate MAC format
if [[ ! "$MAC" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
    echo "Error: Invalid MAC format"
    exit 1
fi

# Remove from MAC ipset
if ipset test hotlist "$MAC" &>/dev/null; then
    ipset del hotlist "$MAC"
    echo "MAC $MAC removed from hotlist"
else
    echo "MAC $MAC not found in hotlist"
fi

# Get IP from ARP/neighbor table
IP=$(ip neigh show dev enp2s0 | grep -i "$MAC" | awk '{print $1}')

# Remove from IP ipset and Nginx whitelist
MAPFILE=/etc/nginx/whitelist.map
touch $MAPFILE

if [ -n "$IP" ]; then
    # Remove IP from hotlist_ip
    if ipset test hotlist_ip "$IP" &>/dev/null; then
        ipset del hotlist_ip "$IP"
        echo "IP $IP removed from hotlist_ip"
    fi

    # Remove from Nginx whitelist map
    grep -v "^$IP " $MAPFILE > ${MAPFILE}.tmp
    mv ${MAPFILE}.tmp $MAPFILE
    echo "IP $IP removed from Nginx whitelist"
    
    # Reload Nginx
    nginx -s reload
else
    echo "IP for MAC $MAC not found; map may already be clear"
fi

