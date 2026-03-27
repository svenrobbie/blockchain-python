# Blockchain Python

A blockchain implementation in Python featuring mining, transactions, node networking, dynamic difficulty, transaction fees, and SQLite persistence.

## Features

- **Mining** - Proof of Work with dynamic difficulty (2-5 leading zeros)
- **Transactions** - UTXO-based with mandatory 1 coin fees
- **Node Network** - P2P networking with mDNS discovery and health monitoring
- **Web UI** - FastAPI-based dashboard for wallet management
- **CLI** - One-shot commands and interactive console mode

## Installation

```bash
# Clone the repository
git clone https://github.com/svenrobbie/blockchain-python
cd blockchain-python

# Install dependencies
pip install -r requirements.txt

# Optional: for web UI
pip install -r web/requirements.txt
```

## Quick Start

```bash
# One-shot commands
python blockchain.py wallet new <password>
python blockchain.py wallet list
python blockchain.py wallet balance
python blockchain.py chain status

# Interactive console
python blockchain.py console

# Start web UI
python blockchain.py start
```

## Project Structure

```
blockchain-python/
├── blockchain.py              # Main entry point
├── blockchain/               # Core blockchain package
│   ├── account.py            # Wallet/account management
│   ├── block.py              # Block class with PoW
│   ├── database.py           # SQLite database layer
│   ├── discovery.py          # mDNS node discovery
│   ├── exceptions.py         # Custom exceptions
│   ├── health.py             # Node health monitoring
│   ├── miner.py              # Mining logic
│   ├── model.py              # Base model class
│   ├── node.py               # Node management
│   ├── rpc.py                # RPC server/client
│   ├── transaction.py        # UTXO transactions
│   └── data/                 # Database storage
├── cli/                      # CLI package
│   ├── commands.py           # One-shot command implementations
│   └── console.py            # Interactive console mode
├── lib/                      # Shared utilities
│   ├── common.py            # Crypto utilities, colored output
│   └── ripemd.py            # RIPEMD160 implementation
└── web/                      # Web UI
    ├── main.py              # FastAPI application
    ├── api/                 # REST API endpoints
    ├── static/              # CSS styles
    └── templates/           # HTML templates
```

## CLI Commands

### Wallet
| Command | Description |
|---------|-------------|
| `wallet new <password>` | Create new wallet |
| `wallet list` | List all accounts |
| `wallet login <index>` | Switch to account |
| `wallet balance` | Show balance |
| `wallet address` | Show current address |

### Transactions
| Command | Description |
|---------|-------------|
| `send <to> <amount> <password>` | Send coins |

### Mining
| Command | Description |
|---------|-------------|
| `mine start` | Start mining |
| `mine stop` | Stop mining |

### Network
| Command | Description |
|---------|-------------|
| `node connect <host:port>` | Add peer node |
| `node list` | List connected nodes |
| `node discover` | Discover nodes via mDNS |

### Blockchain
| Command | Description |
|---------|-------------|
| `chain status` | Chain statistics |
| `chain block <index>` | View block details |
| `chain tx <hash>` | View transaction |
| `chain verify` | Verify chain integrity |

### General
| Command | Description |
|---------|-------------|
| `start` | Start web UI |
| `console` | Interactive mode |
| `status` | Quick status summary |
| `pending` | List pending transactions |

## Configuration

### Dynamic Difficulty
- **Range**: 2-5 leading zeros
- **Adjustment**: Every 10 blocks based on 60s target time
- **Too fast** → difficulty increases
- **Too slow** → difficulty decreases

### Transaction Fees
- **Mandatory**: 1 coin minimum fee
- **Collection**: Miner receives fees + 20 coin reward
- **Display**: Shown in transaction and block details

### Node Health
- **Ping interval**: 60 seconds
- **Timeout**: 10 seconds
- **Max failures**: 5 before removal
- **Discovery**: mDNS broadcasts every 60 seconds

## Web UI

Start the web interface:
```bash
python blockchain.py start
```

Access at `http://localhost:5001` or 'http://127.0.0.1:5001'

Features:
- Dashboard with balance and chain stats
- Send coins interface
- Transaction history
- Block explorer
- Wallet management
