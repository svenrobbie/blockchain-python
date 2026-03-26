# coding:utf-8
import os
import sys
import time
import threading
import getpass

from lib.common import colored, cprint

import node
import miner
import account as account_module
import transaction
import database_sqlite
from exceptions import (
    ValidationError, DoubleSpendError, InvalidAddressError,
    InsufficientFundsError, AmountError, UTXONotFoundError,
    WalletLockedError, InvalidPasswordError
)


BANNER = """
 +------------------------------------------------------------+
 |                                                            |
 |   BBBBB    L      OOOOO   CCCCC  KKKK   KKKK  CCCCCC  HHHH  |
 |   BB  BB   L      OO  OO  CC      KK K  KK KK  CC       HHHH |
 |   BBBBBB   L      OO  OO  CC      KKKK   KKKK  CC       HHHH |
 |   BB  BB   L      OO  OO  CC      KK KK  KK KK  CC       HHHH |
 |   BBBBB    LLLLL   OOOO   CCCCC  KK  K  KK  K  CCCCC  HHHH |
 |                                                            |
 |   P     Y     TTTTT  H     H  OOO   N    N                 |
 |   P     Y       T    H     H  O  O  NN   N                 |
 |   PPPPPPY       T    HHHHHHH  O  O  N N  N                 |
 |   P     Y       T    H     H  OOOO  N  N N                 |
 |                                                            |
 +------------------------------------------------------------+
"""


class Console:
    PROMPT = "blockchain> "

    def __init__(self):
        self.running = True
        self.mining = False
        self.mining_state = {'running': False, 'thread': None}
        self.dashboard_thread = None
        self.dashboard_running = False

    def get_prompt(self):
        account = account_module.get_account()
        if account:
            accounts = account_module.get_accounts()
            for i, acc in enumerate(accounts, 1):
                if acc['address'] == account['address'] and acc.get('is_active'):
                    return f"blockchain[{i}]> "
        return self.PROMPT

    def get_balance(self, address):
        unspent = transaction.Vout.get_unspent(address)
        return sum(vout.amount for vout in unspent)

    def run(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(colored(BANNER, "cyan"))
        print(colored("  Welcome to Blockchain Python v1.0!", "yellow", bold=True))
        print(colored("  Type 'help' for commands or 'dashboard' for live view\n", "white"))

        node.init_node()
        print(colored("  [", "white") + colored("OK", "green") + colored("] Node initialized\n", "white"))

        while self.running:
            try:
                cmd = input(self.get_prompt()).strip()
                if cmd:
                    self.handle_command(cmd)
            except KeyboardInterrupt:
                print("\n")
                if self.mining_state['running']:
                    self.stop_mining()
                if self.dashboard_running:
                    self.stop_dashboard()
                break
            except EOFError:
                break
            except Exception as e:
                print(colored(f"Error: {e}", "red"))

        print(colored("\nGoodbye! Keep on blockchainin'!", "yellow"))

    def handle_command(self, cmd):
        parts = cmd.split()
        if not parts:
            return

        command = parts[0].lower()
        args = parts[1:]

        commands = {
            "help": self.cmd_help,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
            "clear": self.cmd_clear,
            "node": self.cmd_node,
            "miner": self.cmd_miner,
            "mine": self.cmd_mine,
            "wallet": self.cmd_wallet,
            "account": self.cmd_wallet,
            "tx": self.cmd_tx,
            "transaction": self.cmd_tx,
            "send": self.cmd_send,
            "chain": self.cmd_chain,
            "blockchain": self.cmd_chain,
            "pending": self.cmd_pending,
            "status": self.cmd_status,
            "dashboard": self.cmd_dashboard,
            "login": self.cmd_login,
            "logout": self.cmd_logout,
        }

        if command in commands:
            commands[command](args)
        else:
            print(colored(f"Unknown command: {command}", "red"))
            print(colored("Type 'help' for available commands", "yellow"))

    def cmd_help(self, args):
        print(colored("\n=== Available Commands ===\n", "cyan", bold=True))
        
        print(colored("Wallet", "cyan", bold=True))
        print("  wallet create         - Create a new wallet (will prompt for password)")
        print("  wallet address        - Show current account address")
        print("  wallet balance        - Show account balance")
        print("  wallet list          - List all accounts (with index)")
        
        print(colored("\nLogin", "cyan", bold=True))
        print("  login <index> [pw]   - Switch to account by index (optional password)")
        print("  logout               - Logout from current account")
        
        print(colored("\nNode", "cyan", bold=True))
        print("  node start <port>     - Start node server (default: 3009)")
        print("  node add <address>     - Add peer node")
        print("  node list            - List nodes with health status")
        print("  node status          - Show node statistics")
        print("  node discover         - Discover nodes via mDNS")
        
        print(colored("\nMining", "cyan", bold=True))
        print("  mine                 - Start mining (foreground)")
        print("  miner start          - Start mining")
        print("  miner stop           - Stop mining")
        
        print(colored("\nTransactions", "cyan", bold=True))
        print("  tx send <to> <amt>   - Send coins to address")
        print("  tx create <to> <amt>  - Create transaction")
        print("  tx pending           - List pending transactions")
        print("  tx view <hash>       - View transaction details")
        
        print(colored("\nBlockchain", "cyan", bold=True))
        print("  chain status         - Show blockchain status")
        print("  chain view <index>   - View block by index")
        print("  chain info           - Show blockchain info")
        print("  chain verify         - Verify chain integrity")
        
        print(colored("\nGeneral", "cyan", bold=True))
        print("  help                 - Show this help")
        print("  dashboard            - Live updating status view")
        print("  status               - Show overall status")
        print("  clear                - Clear screen")
        print("  exit                 - Exit CLI")

    def cmd_exit(self, args):
        if self.mining_state['running']:
            self.stop_mining()
        self.running = False

    def cmd_login(self, args):
        if not args:
            print(colored("Usage: login <index> [password]", "yellow"))
            print(colored("  index     - Account index (from 'wallet list')", "dim"))
            print(colored("  password  - Optional: Provide password directly", "dim"))
            return
        
        try:
            index = int(args[0])
        except ValueError:
            print(colored("Please provide a valid account index (number)", "red"))
            return
        
        accounts = account_module.get_accounts()
        if index < 1 or index > len(accounts):
            print(colored(f"Invalid index. Available: 1-{len(accounts)}", "red"))
            return
        
        password = args[1] if len(args) > 1 else None
        
        if password:
            try:
                account_module.login(index, password)
                account = accounts[index - 1]
                print(colored(f"\nLogged in to account {index}", "green", bold=True))
                print(f"Address: {colored(account['address'], 'cyan')}")
            except InvalidPasswordError:
                print(colored("Invalid password", "red"))
            except Exception as e:
                print(colored(f"Login failed: {e}", "red"))
        else:
            if account_module.login(index):
                account = accounts[index - 1]
                print(colored(f"\nLogged in to account {index}", "green", bold=True))
                print(f"Address: {colored(account['address'], 'cyan')}")
                if account.get('encrypted_key'):
                    print(colored("\nNote: Provide password to unlock for transactions", "yellow"))
            else:
                print(colored("Login failed", "red"))

    def cmd_logout(self, args):
        account = account_module.get_account()
        if not account:
            print(colored("No account is currently logged in", "yellow"))
            return
        
        account_module.logout()
        print(colored("Logged out successfully", "green"))
        print(colored("Create or login to an account to continue", "yellow"))

    def cmd_clear(self, args):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(colored(BANNER, "cyan"))
        print(colored("  Welcome to Blockchain Python v1.0!", "yellow", bold=True))
        print(colored("  Type 'help' for commands or 'dashboard' for live view\n", "white"))

    def cmd_dashboard(self, args):
        if self.dashboard_running:
            print(colored("Dashboard already running! Press Ctrl+C to exit.", "yellow"))
            return
        
        print(colored("\n+==============================================================+", "cyan"))
        print(colored("|              LIVE BLOCKCHAIN DASHBOARD                       |", "cyan"))
        print(colored("+==============================================================+", "cyan"))
        print(colored("  Press Ctrl+C to return to CLI\n", "white"))
        
        self.dashboard_running = True
        self.dashboard_thread = threading.Thread(target=self._dashboard_loop, daemon=True)
        self.dashboard_thread.start()

    def _dashboard_loop(self):
        while self.dashboard_running:
            self._print_dashboard()
            time.sleep(2)

    def _print_dashboard(self):
        bcdb = database_sqlite.BlockChainDB()
        chain = bcdb.find_all()
        txdb = database_sqlite.TransactionDB()
        transactions = txdb.find_all()
        untxdb = database_sqlite.UnTransactionDB()
        pending = untxdb.find_all()
        account = account_module.get_account()
        balance = self.get_balance(account['address']) if account else 0
        
        raw_status = node.get_node_status()
        if not raw_status:
            node_status = []
        elif isinstance(raw_status, list):
            node_status = [n for n in raw_status if isinstance(n, dict)]
        elif isinstance(raw_status, dict):
            node_status = [raw_status]
        else:
            node_status = []
        alive_nodes = sum(1 for n in node_status if n.get('is_alive', False))
        
        last_block = chain[-1] if chain else None
        block_time = time.strftime('%H:%M:%S', time.localtime(last_block['timestamp'])) if last_block else 'N/A'
        
        total_fees = sum(b.get('fees_collected', 0) for b in chain)
        
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(colored("+==============================================================+", "cyan"))
        print(colored("|              LIVE BLOCKCHAIN DASHBOARD                       |", "cyan"))
        print(colored("+==============================================================+", "cyan"))
        print()
        
        print(colored("  +--------------------+  +--------------------+", "white"))
        print(colored("  | BLOCK #: ", "white") + colored(f"{len(chain):>6}", "green", bold=True) + colored(" |  | ", "white") + 
              colored("MINING: ", "white") + colored("ON " if self.mining_state['running'] else "OFF", "yellow" if self.mining_state['running'] else "red", bold=True) + 
              colored("    |"))
        print(colored("  | PENDING TX: ", "white") + colored(f"{len(pending):>4}", "yellow", bold=True) + colored(" |  | ", "white") +
              colored("NODES: ", "white") + colored(f"{alive_nodes:>6}", "cyan", bold=True) + colored(" |"))
        print(colored("  +--------------------+  +--------------------+", "white"))
        print()
        
        print(colored("  +--------------------+  +--------------------+", "white"))
        print(colored("  | BALANCE: ", "white") + colored(f"{balance:>6}", "green", bold=True) + 
              colored(" coins  |  | ", "white") +
              colored("FEES: ", "white") + colored(f"{total_fees:>6}", "yellow", bold=True) + 
              colored(" total  |"))
        print(colored("  | LAST BLOCK: ", "white") + colored(f"{block_time:>8}", "cyan", bold=True) + 
              colored(" |  | ", "white") +
              colored("CONFIRMED: ", "white") + colored(f"{len(transactions):>4}", "green", bold=True) + 
              colored(" tx   |"))
        print(colored("  +--------------------+  +--------------------+", "white"))
        print()
        
        if last_block:
            print(colored("  Latest Block:", "cyan", bold=True))
            print(colored("    Hash: ", "white") + colored(f"{last_block.get('hash', 'N/A')[:30]}...", "yellow"))
            print(colored("    Difficulty: ", "white") + colored(f"{last_block.get('difficulty', 5)}", "cyan") + 
                  colored(" zeros | Nonce: ", "white") + colored(f"{last_block.get('nouce', 0):,}", "cyan"))
            print(colored("    Transactions: ", "white") + colored(f"{len(last_block.get('tx', []))}", "green"))
        
        print()
        print(colored("  Press Ctrl+C to return to CLI", "dim"))

    def stop_dashboard(self):
        self.dashboard_running = False

    def cmd_status(self, args):
        bcdb = database_sqlite.BlockChainDB()
        chain = bcdb.find_all()
        txdb = database_sqlite.TransactionDB()
        transactions = txdb.find_all()
        untxdb = database_sqlite.UnTransactionDB()
        pending = untxdb.find_all()

        account = account_module.get_account()
        if account:
            balance = self.get_balance(account['address'])
        else:
            balance = 0

        print(colored("\n=== Blockchain Status ===", "cyan", bold=True))
        print(f"Blocks:      {colored(str(len(chain)), 'green')} ")
        print(f"Tx Confirmed: {colored(str(len(transactions)), 'green')} ")
        print(f"Tx Pending:   {colored(str(len(pending)), 'yellow')} ")
        print(f"Mining:      {colored('Yes' if self.mining_state['running'] else 'No', 'green' if not self.mining_state['running'] else 'yellow')} ")
        print(f"Balance:     {colored(str(balance), 'green')} coins")
        if account:
            print(f"Address:     {colored(account['address'][:20] + '...', 'white')} ")

    def cmd_node(self, args):
        if not args:
            print(colored("Usage: node <start|add|list|status|discover>", "yellow"))
            return

        subcmd = args[0].lower()

        if subcmd == "start":
            port = int(args[1]) if len(args) > 1 else 3009
            print(colored(f"Starting node on port {port}...", "cyan"))
            node.start_node(f"0.0.0.0:{port}")
            print(colored("Node started", "green"))
            print(colored("  - RPC server started", "white"))
            print(colored("  - mDNS discovery enabled", "white"))
            print(colored("  - Health monitor enabled (60s interval)", "white"))

        elif subcmd == "add":
            if len(args) < 2:
                print(colored("Usage: node add <address>", "yellow"))
                return
            address = args[1]
            if address.find('http') != 0:
                address = 'http://' + address
            node.add_node(address)
            print(colored(f"Added node: {address}", "green"))

        elif subcmd == "list":
            nodes = node.get_nodes_status()
            print(colored("\n=== Connected Nodes ===", "cyan", bold=True))
            if nodes:
                for i, n in enumerate(nodes, 1):
                    status_color = 'green' if n['is_alive'] else 'red'
                    status_text = 'ONLINE' if n['is_alive'] else 'OFFLINE'
                    last_seen = n['last_seen']
                    if last_seen > 0:
                        from datetime import datetime
                        last_seen_str = datetime.fromtimestamp(last_seen).strftime('%H:%M:%S')
                    else:
                        last_seen_str = 'Never'
                    print(f"\n  {i}. {colored(n['address'], 'cyan')}")
                    print(f"     Status: {colored(status_text, status_color)}")
                    print(f"     Last seen: {colored(last_seen_str, 'yellow')}")
            else:
                print(colored("  No nodes configured", "yellow"))

        elif subcmd == "status":
            status = node.get_node_status()
            if not isinstance(status, list):
                status = [status] if status else []
            print(colored("\n=== Node Status ===", "cyan", bold=True))
            alive = sum(1 for n in status if n.get('is_alive', False))
            total = len(status)
            print(f"  Total nodes: {colored(str(total), 'white')}")
            print(f"  Online: {colored(str(alive), 'green')}")
            print(f"  Offline: {colored(str(total - alive), 'red')}")

        elif subcmd == "discover":
            print(colored("\n=== Discovering Nodes ===", "cyan", bold=True))
            print(colored("Scanning local network for Blockchain_Python nodes...", "white"))
            try:
                from node_discovery import auto_discover_nodes
                discovered = auto_discover_nodes(timeout=5)
                if discovered:
                    print(colored(f"\nFound {len(discovered)} node(s):", "green"))
                    for n in discovered:
                        print(f"  - {colored(n['address'], 'cyan')} (v{n['version']})")
                        node.add_node(n['address'])
                else:
                    print(colored("No nodes found on network", "yellow"))
            except Exception as e:
                print(colored(f"Discovery failed: {e}", "red"))
                print(colored("Install zeroconf: pip install zeroconf", "yellow"))

        elif subcmd == "ping":
            if len(args) < 2:
                print(colored("Usage: node ping <address>", "yellow"))
                return
            address = args[1]
            if address.find('http') != 0:
                address = 'http://' + address
            print(colored(f"Pinging {address}...", "white"))
            try:
                from node_health import ping_node
                result = ping_node(address)
                if result:
                    print(colored("Node is alive!", "green"))
                else:
                    print(colored("Node is unreachable", "red"))
            except Exception as e:
                print(colored(f"Ping failed: {e}", "red"))

        else:
            print(colored(f"Unknown node command: {subcmd}", "red"))

    def cmd_miner(self, args):
        if not args:
            print(colored("Usage: miner <start|stop>", "yellow"))
            return

        subcmd = args[0].lower()

        if subcmd == "start" or subcmd == "mine":
            self.start_mining()

        elif subcmd == "stop":
            self.stop_mining()

        else:
            print(colored(f"Unknown miner command: {subcmd}", "red"))

    def cmd_mine(self, args):
        self.start_mining()

    def start_mining(self):
        if self.mining_state['running']:
            print(colored("Mining already in progress!", "yellow"))
            return

        print(colored("\n=== Starting Mining ===", "cyan", bold=True))
        print(colored("Press Ctrl+C to stop\n", "yellow"))

        self.mining_state['running'] = True
        self.mining_state['thread'] = threading.Thread(target=self._mining_loop, daemon=True)
        self.mining_state['thread'].start()

    def _mining_loop(self):
        while self.mining_state['running']:
            try:
                print(colored(f"[{time.strftime('%H:%M:%S')}] ", "dim") + "Mining block...", end="\r")
                block = miner.mine()
                print(colored(f"[{time.strftime('%H:%M:%S')}] ", "dim") +
                      colored(f"Block #{block.index} ", "green", bold=True) +
                      f"mined! (nonce={block.nouce}, diff={block.difficulty})")
                time.sleep(1)
            except KeyboardInterrupt:
                self.mining_state['running'] = False
                break
            except Exception as e:
                if self.mining_state['running']:
                    print(colored(f"\nMining error: {e}", "red"))
                    time.sleep(5)

    def stop_mining(self):
        if not self.mining_state['running']:
            print(colored("Mining not running", "yellow"))
            return

        print(colored("\nStopping mining...", "yellow"))
        self.mining_state['running'] = False
        if self.mining_state['thread']:
            self.mining_state['thread'].join(timeout=2)
        print(colored("Mining stopped", "green"))

    def cmd_wallet(self, args):
        if not args:
            print(colored("Usage: wallet <create|address|balance|list>", "yellow"))
            return

        subcmd = args[0].lower()

        if subcmd == "create" or subcmd == "new":
            self.wallet_create()

        elif subcmd == "address" or subcmd == "addr":
            self.wallet_address()

        elif subcmd == "balance" or subcmd == "bal":
            self.wallet_balance()

        elif subcmd == "list" or subcmd == "all":
            self.wallet_list()

        else:
            print(colored(f"Unknown wallet command: {subcmd}", "red"))

    def wallet_create(self):
        print(colored("\nCreating new wallet...", "cyan"))
        
        password = getpass.getpass("Enter password to encrypt wallet: ")
        if not password:
            print(colored("Password cannot be empty", "red"))
            return
        
        password2 = getpass.getpass("Confirm password: ")
        if password != password2:
            print(colored("Passwords do not match", "red"))
            return
        
        private_key, public_key, address = account_module.new_account(password)
        
        print(colored("\n=== New Wallet Created ===", "green", bold=True))
        print(f"Address: {colored(address, 'cyan', bold=True)}")
        print(colored("\nWallet encrypted and saved securely.", "green"))
        print(colored("You will need your password to send transactions.", "yellow"))

    def wallet_address(self):
        account = account_module.get_account()
        if account:
            accounts = account_module.get_accounts()
            for i, acc in enumerate(accounts, 1):
                if acc['address'] == account['address']:
                    print(colored("\n=== Current Account ===", "cyan", bold=True))
                    print(f"Index:   {colored(str(i), 'yellow')}")
                    print(f"Address: {colored(account['address'], 'cyan', bold=True)}")
                    return
        else:
            print(colored("No account found. Create one with 'wallet create'", "yellow"))

    def wallet_balance(self):
        account = account_module.get_account()
        if not account:
            print(colored("No account found. Create one with 'wallet create'", "yellow"))
            return

        balance = self.get_balance(account['address'])
        print(colored("\n=== Balance ===", "cyan", bold=True))
        print(f"Address: {colored(account['address'], 'white')}")
        print(f"Balance: {colored(str(balance), 'green', bold=True)} coins")

    def wallet_list(self):
        accounts = account_module.get_accounts()
        print(colored("\n=== All Accounts ===", "cyan", bold=True))
        if accounts:
            for i, acc in enumerate(accounts, 1):
                balance = self.get_balance(acc['address'])
                active_marker = colored(" <-- active", "green", bold=True) if acc.get('is_active') else ""
                print(f"\n{i}. {colored(acc['address'][:30] + '...', 'cyan')}{active_marker}")
                print(f"   Balance: {colored(str(balance), 'green')} coins")
        else:
            print(colored("No accounts found", "yellow"))
        print(colored("\n  Use 'login <index>' to switch accounts", "dim"))

    def cmd_tx(self, args):
        if not args:
            print(colored("Usage: tx <send|pending|view>", "yellow"))
            return

        subcmd = args[0].lower()

        if subcmd == "send" or subcmd == "create":
            if len(args) < 3:
                print(colored("Usage: tx send <to_address> <amount>", "yellow"))
                return
            to_address = args[1]
            amount = int(args[2])
            self.tx_send(to_address, amount)

        elif subcmd == "pending":
            self.tx_pending()

        elif subcmd == "view":
            if len(args) < 2:
                print(colored("Usage: tx view <hash>", "yellow"))
                return
            tx_hash = args[1]
            self.tx_view(tx_hash)

        else:
            print(colored(f"Unknown tx command: {subcmd}", "red"))

    def cmd_send(self, args):
        if len(args) < 2:
            print(colored("Usage: send <to_address> <amount>", "yellow"))
            return
        to_address = args[0]
        amount = int(args[1])
        self.tx_send(to_address, amount)

    def tx_send(self, to_address, amount):
        account = account_module.get_account()
        if not account:
            print(colored("No account found. Create one with 'wallet create' or 'login <index>'", "yellow"))
            return

        from_address = account['address']
        balance = self.get_balance(from_address)

        print(colored(f"\nSending {amount} coins to {to_address}...", "cyan"))
        print(f"From: {colored(from_address, 'white')}")
        print(f"To:   {colored(to_address, 'white')}")
        print(f"Amount: {colored(str(amount), 'green')} coins")
        print(f"Balance: {colored(str(balance), 'yellow')} coins")

        password = getpass.getpass("\nEnter password to unlock wallet: ")
        if not password:
            print(colored("Password required to send transactions", "red"))
            return

        try:
            unlocked = account_module.unlock_account(from_address, password)
            if not unlocked or not unlocked.get('private_key'):
                print(colored("Failed to unlock wallet - check password", "red"))
                return
            private_key = unlocked['private_key']
        except InvalidPasswordError:
            print(colored("Invalid password", "red"))
            return
        except Exception as e:
            print(colored(f"Failed to unlock wallet: {e}", "red"))
            return

        try:
            tx_dict = transaction.Transaction.transfer(from_address, to_address, amount, private_key=private_key)
            print(colored("\nTransaction created!", "green", bold=True))
            print(f"TX Hash: {colored(tx_dict['hash'], 'cyan')}")
            print(colored("\nTransaction is pending. It will be mined soon.", "yellow"))
            transaction.Transaction.unblock_spread(tx_dict)
        except InsufficientFundsError as e:
            print(colored(f"\nError: Insufficient funds!", "red", bold=True))
            print(f"  Your balance: {colored(str(balance), 'yellow')} coins")
        except InvalidAddressError as e:
            print(colored(f"\nError: Invalid address!", "red", bold=True))
        except DoubleSpendError as e:
            print(colored(f"\nError: Double spend detected!", "red", bold=True))
        except AmountError as e:
            print(colored(f"\nError: Invalid amount!", "red", bold=True))
        except UTXONotFoundError as e:
            print(colored(f"\nError: UTXO not found!", "red", bold=True))
        except ValidationError as e:
            print(colored(f"\nError: Validation failed!", "red", bold=True))
        except Exception as e:
            print(colored(f"\nTransaction failed: {e}", "red"))

    def tx_pending(self):
        untxdb = database_sqlite.UnTransactionDB()
        pending = untxdb.find_all()
        print(colored("\n=== Pending Transactions ===", "cyan", bold=True))
        if pending:
            for i, tx in enumerate(pending, 1):
                print(f"\n{i}. Hash: {colored(tx['hash'][:20] + '...', 'cyan')}")
                print(f"   Timestamp: {tx.get('timestamp', 'N/A')}")
                print(f"   Inputs: {len(tx.get('vin', []))}")
                print(f"   Outputs: {len(tx.get('vout', []))}")
                print(f"   Fee: {colored(str(tx.get('fee', 1)), 'yellow')} coins")
        else:
            print(colored("No pending transactions", "yellow"))

    def tx_view(self, tx_hash):
        txdb = database_sqlite.TransactionDB()
        untxdb = database_sqlite.UnTransactionDB()

        all_txs = txdb.find_all() + untxdb.find_all()

        for tx in all_txs:
            if tx['hash'] == tx_hash:
                print(colored(f"\n=== Transaction ===", "cyan", bold=True))
                print(f"Hash: {colored(tx['hash'], 'cyan')}")
                print(f"Timestamp: {tx.get('timestamp', 'N/A')}")
                print(f"Fee: {colored(str(tx.get('fee', 1)), 'yellow')} coins")
                print(f"\nInputs ({len(tx.get('vin', []))}):")
                for vin in tx.get('vin', []):
                    print(f"  - {colored(vin.get('hash', 'N/A')[:20] + '...', 'white')} ({vin.get('amount', 0)} coins)")
                print(f"\nOutputs ({len(tx.get('vout', []))}):")
                for vout in tx.get('vout', []):
                    print(f"  -> {colored(vout.get('receiver', 'N/A')[:20] + '...', 'cyan')} ({vout.get('amount', 0)} coins)")
                return

        print(colored(f"Transaction not found: {tx_hash}", "red"))

    def cmd_chain(self, args):
        if not args:
            print(colored("Usage: chain <status|view|info|verify>", "yellow"))
            return

        subcmd = args[0].lower()

        if subcmd == "status":
            self.chain_status()

        elif subcmd == "view":
            index = int(args[1]) if len(args) > 1 else -1
            self.chain_view(index)

        elif subcmd == "info":
            self.chain_info()

        elif subcmd == "verify":
            self.chain_verify()

        else:
            print(colored(f"Unknown chain command: {subcmd}", "red"))

    def chain_status(self):
        bcdb = database_sqlite.BlockChainDB()
        chain = bcdb.find_all()

        print(colored("\n=== Chain Status ===", "cyan", bold=True))
        print(f"Total blocks: {colored(str(len(chain)), 'green')}")

        if chain:
            last = chain[-1]
            first = chain[0]

            if len(chain) > 1:
                total_time = last['timestamp'] - first['timestamp']
                avg_time = total_time / (len(chain) - 1)
                print(f"Average block time: {colored(f'{avg_time:.1f}s', 'yellow')}")

            print(f"Latest block: {colored('#' + str(last['index']), 'green', bold=True)}")
            print(f"Difficulty: {colored(str(last.get('difficulty', 5)), 'cyan')}")
            print(f"Hash: {colored(last.get('hash', 'N/A')[:20] + '...', 'white')}")

    def chain_view(self, index):
        bcdb = database_sqlite.BlockChainDB()
        chain = bcdb.find_all()

        if index == -1:
            index = len(chain) - 1

        if index < 0 or index >= len(chain):
            print(colored(f"Block not found. Valid range: 0-{len(chain)-1}", "red"))
            return

        block = chain[index]
        fees = block.get('fees_collected', 0)
        miner_reward = 20 + fees
        print(colored(f"\n=== Block #{block['index']} ===", "cyan", bold=True))
        print(f"Timestamp:    {block['timestamp']} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block['timestamp']))})")
        print(f"Hash:         {colored(block.get('hash', 'N/A'), 'white')}")
        print(f"Prev Hash:    {colored(block.get('previous_block', 'N/A'), 'white')}")
        print(f"Difficulty:   {colored(str(block.get('difficulty', 5)), 'cyan')} ({block.get('difficulty', 5)} leading zeros)")
        print(f"Nonce:        {block.get('nouce', 'N/A')}")
        print(f"Fees:         {colored(str(fees), 'yellow')} coins")
        print(f"Miner reward: {colored(str(miner_reward), 'green')} coins (20 base + {fees} fees)")
        print(f"Transactions: {colored(str(len(block.get('tx', []))), 'green')}")
        for i, tx_hash in enumerate(block.get('tx', [])):
            print(f"  {i+1}. {tx_hash[:40]}...")

    def chain_info(self):
        bcdb = database_sqlite.BlockChainDB()
        chain = bcdb.find_all()

        if not chain:
            print(colored("No blocks in chain", "yellow"))
            return

        difficulties = [b.get('difficulty', 5) for b in chain]
        nonces = [b.get('nouce', 0) for b in chain]
        total_fees = sum(b.get('fees_collected', 0) for b in chain)

        print(colored("\n=== Chain Info ===", "cyan", bold=True))
        print(f"Total blocks:      {colored(str(len(chain)), 'green')}")
        print(f"Genesis block:     {colored(chain[0]['hash'][:20] + '...', 'white')}")
        print(f"Latest block:      {colored(chain[-1]['hash'][:20] + '...', 'white')}")
        print(f"Current difficulty: {colored(str(difficulties[-1]), 'cyan')}")
        print(f"Difficulty range:  {min(difficulties)} - {max(difficulties)}")
        print(f"Total fees mined:  {colored(str(total_fees), 'yellow')} coins")
        print(f"Average nonce:     {sum(nonces) // len(nonces):,}")

        if len(chain) >= 10:
            recent_diffs = [chain[i+1]['timestamp'] - chain[i]['timestamp']
                           for i in range(len(chain)-10, len(chain)-1)]
            print(f"Last 10 avg time:  {sum(recent_diffs) // len(recent_diffs)}s")

    def chain_verify(self):
        bcdb = database_sqlite.BlockChainDB()
        chain = bcdb.find_all()

        print(colored("\n=== Verifying Chain ===", "cyan", bold=True))
        print(f"Blocks to verify: {len(chain)}\n")

        if not chain:
            print(colored("No blocks to verify", "yellow"))
            return

        def progress_callback(current, total):
            pct = int(100 * current / total) if total > 0 else 100
            bar_length = 30
            filled = int(bar_length * current / total) if total > 0 else bar_length
            bar = '=' * filled + '-' * (bar_length - filled)
            print(f"\r  [{bar}] {current + 1}/{total} ({pct}%)", end='', flush=True)
            if current == total - 1:
                print()

        print(colored("Validating blocks and transactions...", "yellow"))
        valid, error = node.validate_chain(chain, progress_callback)

        if valid:
            print(colored("\nVerification PASSED!", "green", bold=True))
            print(colored(f"  - {len(chain)} blocks validated", "green"))
            print(colored("  - All transactions verified", "green"))
            print(colored("  - Chain integrity confirmed", "green"))
        else:
            print(colored("\nVerification FAILED!", "red", bold=True))
            print(colored(f"  Error: {error}", "red"))

    def cmd_pending(self, args):
        self.tx_pending()
