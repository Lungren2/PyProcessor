#!/bin/bash

# TCP optimizations
echo "Configuring network settings..."
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 16777216"
sudo sysctl -w net.ipv4.tcp_wmem="4096 65536 16777216"
sudo sysctl -w net.ipv4.tcp_window_scaling=1
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=8192
sudo sysctl -w net.ipv4.tcp_syncookies=1

# Make changes permanent
sudo tee -a /etc/sysctl.conf <<EOF
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
net.ipv4.tcp_window_scaling=1
net.ipv4.tcp_max_syn_backlog=8192
net.ipv4.tcp_syncookies=1
EOF

# Apply changes
sudo sysctl -p

# Install required software (Ubuntu/Debian example)
sudo apt update
sudo apt install -y nginx apache2-utils