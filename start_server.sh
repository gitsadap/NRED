#!/bin/bash

# Find likely IP address (Mac/Linux)
IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)

echo "-----------------------------------------------------"
echo "Starting Department NRE Server on LAN..."
echo "-----------------------------------------------------"
echo "Local Access:     http://localhost:8099"
if [ ! -z "$IP" ]; then
    echo "LAN Access:       http://$IP:8099"
    echo " (Use this URL on other devices in the same WiFi)"
else
    echo "LAN Access:       (Could not detect IP, check network settings)"
fi
echo "-----------------------------------------------------"
echo "Press Ctrl+C to stop."

php -S 0.0.0.0:8099 -t public
