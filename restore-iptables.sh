#!/bin/bash

# Check if hotlist exists
if ! ipset list hotlist >/dev/null 2>&1; then
    # Restore hotlist since it doesn't exist
    ipset restore -f /etc/ipset.conf
else
    echo "Hotlist already exists, skipping restore."
fi

# Restore iptables rules
iptables-restore /etc/iptables/rules.v4


