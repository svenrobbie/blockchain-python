# coding:utf-8
"""
Blockchain Configuration

All magic numbers and configuration values in one place.
"""

# Network Ports
WEB_PORT = 5001
NODE_RPC_PORT = 3009
DISCOVERY_PORT = 3009

# Mining
MINING_REWARD = 2.5

# Transaction
MIN_FEE = 0.0001

# Blockchain
MIN_DIFFICULTY = 2
MAX_DIFFICULTY = 5
TARGET_BLOCK_TIME = 60
ADJUSTMENT_WINDOW = 10

# Node Health
PING_INTERVAL = 60
PING_TIMEOUT = 10
MAX_FAILURES = 5

# Discovery
DISCOVERY_INTERVAL = 60

# Version
VERSION = "1.0"
