# Blockchain Python

A blockchain implementation in Python for learning and experimentation.

Features: Mining, Transactions, Node Network, Dynamic Difficulty, Transaction Fees, and SQLite Persistence.

## Installation

1. Make sure [Python 3.6+](https://www.python.org/downloads/) is installed
2. Install dependencies:
```bash
pip install zeroconf
```
3. Run the CLI:
```bash
python cli.py
```

## Quick Start

```bash
# Create a wallet
wallet create

# Start mining
mine

# Send coins
tx send <address> <amount>

# View blockchain
chain info
chain view

# Dashboard mode
dashboard
```

## CLI Commands

### Wallet
| Command | Description |
|---------|-------------|
| `wallet create` | Create a new wallet |
| `wallet address` | Show current account address |
| `wallet balance` | Show account balance |
| `wallet list` | List all accounts |

### Mining
| Command | Description |
|---------|-------------|
| `mine` | Start mining (foreground) |
| `miner start` | Start mining |
| `miner stop` | Stop mining |

### Transactions
| Command | Description |
|---------|-------------|
| `tx send <to> <amount>` | Send coins to address |
| `tx pending` | List pending transactions |
| `tx view <hash>` | View transaction details |

### Blockchain
| Command | Description |
|---------|-------------|
| `chain status` | Show blockchain status |
| `chain view <index>` | View block by index |
| `chain info` | Show blockchain info |
| `chain verify` | Verify chain integrity |

### Node Network
| Command | Description |
|---------|-------------|
| `node start <port>` | Start node server (default: 3009) |
| `node add <address>` | Add peer node |
| `node list` | List nodes with health status |
| `node status` | Show node statistics |
| `node discover` | Discover nodes via mDNS |
| `node ping <addr>` | Ping a specific node |

### General
| Command | Description |
|---------|-------------|
| `dashboard` | Live updating status view |
| `status` | Show overall status |
| `help` | Show this help |
| `clear` | Clear screen |
| `exit` | Exit CLI |

## Features

### Dynamic Difficulty
Block difficulty automatically adjusts based on mining speed:
- Mining too fast → difficulty increases
- Mining too slow → difficulty decreases
- Range: 2-5 leading zeros
- Adjustment: Every 10 blocks

### Transaction Fees
- Mandatory 1 coin fee per transaction
- Miner collects fees in addition to block reward
- Fee displayed in transaction and block details

### Node Network
- **mDNS Discovery**: Automatically discovers other nodes on local network
- **Health Monitoring**: Pings all nodes every 60 seconds
- **Auto-recovery**: Removes dead nodes after 5 consecutive failures

### Database
- SQLite for fast, reliable storage
- Automatic migration for schema updates

## Architecture

```
cli.py              # Interactive CLI interface
block.py            # Block class with PoW
miner.py            # Mining logic with fees
transaction.py      # Transaction/UTXO logic
node.py             # Node management
node_discovery.py   # mDNS service discovery
node_health.py      # Node health monitoring
rpc.py              # RPC server/client
database_sqlite.py   # SQLite database layer
```

## Security Notes

This is an educational implementation. For production use, you would need:
- Transaction signing (ECDSA)
- Signature verification
- UTXO validation
- Merkle tree verification
- TLS encryption for RPC
- Consensus algorithm improvements

## License

MIT
