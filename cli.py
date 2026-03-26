# coding:utf-8
import sys
import time
import threading
from lib.common import colored, cprint

import node
import miner
import account as account_module
import transaction
import database
import block as block_module


class BlockchainCLI:
    PROMPT = "blockchain> "

    def __init__(self):
        self.running = True
        self.mining = False
        self.mining_thread = None

    def start(self):
        print(colored("\n=== Blockchain CLI ===", "cyan", bold=True))
        print(colored("Type 'help' for commands\n", "white"))

        node.init_node()
        cprint("INFO", "Node initialized")

        while self.running:
            try:
                cmd = input(self.PROMPT).strip()
                if cmd:
                    self.handle_command(cmd)
            except KeyboardInterrupt:
                print("\n")
                if self.mining:
                    self.stop_mining()
                break
            except EOFError:
                break
            except Exception as e:
                print(colored(f"Error: {e}", "red"))

        print(colored("Goodbye!", "yellow"))

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
        }

        if command in commands:
            commands[command](args)
        else:
            print(colored(f"Unknown command: {command}", "red"))
            print(colored("Type 'help' for available commands", "yellow"))

    def cmd_help(self, args):
        print(colored("\n=== Available Commands ===\n", "cyan", bold=True))
        
        print(colored("Wallet", "cyan", bold=True))
        print("  wallet create         - Create a new wallet")
        print("  wallet address        - Show current account address")
        print("  wallet balance        - Show account balance")
        print("  wallet list          - List all accounts")
        
        print(colored("\nNode", "cyan", bold=True))
        print("  node start <port>     - Start node server (default: 3009)")
        print("  node add <address>    - Add peer node")
        print("  node list            - List connected nodes")
        
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
        print("  status               - Show overall status")
        print("  clear                - Clear screen")
        print("  exit                 - Exit CLI")

    def cmd_exit(self, args):
        if self.mining:
            self.stop_mining()
        self.running = False

    def cmd_clear(self, args):
        print("\033[2J\033[H", end="")

    def cmd_status(self, args):
        bcdb = database.BlockChainDB()
        chain = bcdb.find_all()
        txdb = database.TransactionDB()
        transactions = txdb.find_all()
        untxdb = database.UnTransactionDB()
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
        print(f"Mining:      {colored('Yes' if self.mining else 'No', 'green' if not self.mining else 'yellow')} ")
        print(f"Balance:     {colored(str(balance), 'green')} coins")
        if account:
            print(f"Address:     {colored(account['address'][:20] + '...', 'white')} ")

    def cmd_node(self, args):
        if not args:
            print(colored("Usage: node <start|add|list>", "yellow"))
            return

        subcmd = args[0].lower()

        if subcmd == "start":
            port = int(args[1]) if len(args) > 1 else 3009
            print(colored(f"Starting node on port {port}...", "cyan"))
            node.start_node(f"0.0.0.0:{port}")
            print(colored("Node started", "green"))

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
            nodes = node.get_nodes()
            print(colored("\n=== Connected Nodes ===", "cyan", bold=True))
            if nodes:
                for i, n in enumerate(nodes, 1):
                    print(f"  {i}. {colored(n, 'green')}")
            else:
                print(colored("  No nodes connected", "yellow"))

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
        if self.mining:
            print(colored("Mining already in progress!", "yellow"))
            return

        print(colored("\n=== Starting Mining ===", "cyan", bold=True))
        print(colored("Press Ctrl+C to stop\n", "yellow"))

        self.mining = True
        self.mining_thread = threading.Thread(target=self._mining_loop, daemon=True)
        self.mining_thread.start()

    def _mining_loop(self):
        while self.mining:
            try:
                print(colored(f"[{time.strftime('%H:%M:%S')}] ", "dim") + "Mining block...", end="\r")
                block = miner.mine()
                print(colored(f"[{time.strftime('%H:%M:%S')}] ", "dim") +
                      colored(f"Block #{block.index} ", "green", bold=True) +
                      f"mined! (nonce={block.nouce}, diff={block.difficulty})")
                time.sleep(1)
            except Exception as e:
                if self.mining:
                    print(colored(f"\nMining error: {e}", "red"))
                    time.sleep(5)

    def stop_mining(self):
        if not self.mining:
            print(colored("Mining not running", "yellow"))
            return

        print(colored("\nStopping mining...", "yellow"))
        self.mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=2)
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
        private_key, public_key, address = account_module.new_account()
        print(colored("\n=== New Wallet Created ===", "green", bold=True))
        print(f"Address: {colored(address, 'cyan', bold=True)}")
        print(f"Public Key: {colored(public_key[:20] + '...', 'white')}")
        print(colored("\nIMPORTANT: Save your private key!", "red", bold=True))
        print(f"Private Key: {colored(private_key, 'yellow')}")

    def wallet_address(self):
        account = account_module.get_account()
        if account:
            print(colored("\n=== Current Account ===", "cyan", bold=True))
            print(f"Address: {colored(account['address'], 'cyan', bold=True)}")
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
        adb = database.AccountDB()
        accounts = adb.find_all()
        print(colored("\n=== All Accounts ===", "cyan", bold=True))
        if accounts:
            for i, acc in enumerate(accounts, 1):
                balance = self.get_balance(acc['address'])
                print(f"\n{i}. {colored(acc['address'][:30] + '...', 'cyan')}")
                print(f"   Balance: {colored(str(balance), 'green')} coins")
        else:
            print(colored("No accounts found", "yellow"))

    def get_balance(self, address):
        unspent = transaction.Vout.get_unspent(address)
        return sum(vout.amount for vout in unspent)

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
            print(colored("No account found. Create one with 'wallet create'", "yellow"))
            return

        from_address = account['address']
        balance = self.get_balance(from_address)

        if balance < amount:
            print(colored(f"Insufficient balance! You have {balance} coins", "red"))
            return

        print(colored(f"\nSending {amount} coins to {to_address}...", "cyan"))
        print(f"From: {colored(from_address, 'white')}")
        print(f"To:   {colored(to_address, 'white')}")
        print(f"Amount: {colored(str(amount), 'green')} coins")
        print(f"Balance: {colored(str(balance), 'yellow')} coins")

        try:
            tx_dict = transaction.Transaction.transfer(from_address, to_address, amount)
            print(colored("\nTransaction created!", "green", bold=True))
            print(f"TX Hash: {colored(tx_dict['hash'], 'cyan')}")
            print(colored("\nTransaction is pending. It will be mined soon.", "yellow"))
            transaction.Transaction.unblock_spread(tx_dict)
        except Exception as e:
            print(colored(f"Transaction failed: {e}", "red"))

    def tx_pending(self):
        untxdb = database.UnTransactionDB()
        pending = untxdb.find_all()
        print(colored("\n=== Pending Transactions ===", "cyan", bold=True))
        if pending:
            for i, tx in enumerate(pending, 1):
                print(f"\n{i}. Hash: {colored(tx['hash'][:20] + '...', 'cyan')}")
                print(f"   Timestamp: {tx.get('timestamp', 'N/A')}")
                print(f"   Inputs: {len(tx.get('vin', []))}")
                print(f"   Outputs: {len(tx.get('vout', []))}")
        else:
            print(colored("No pending transactions", "yellow"))

    def tx_view(self, tx_hash):
        txdb = database.TransactionDB()
        untxdb = database.UnTransactionDB()

        all_txs = txdb.find_all() + untxdb.find_all()

        for tx in all_txs:
            if tx['hash'] == tx_hash:
                print(colored(f"\n=== Transaction ===", "cyan", bold=True))
                print(f"Hash: {colored(tx['hash'], 'cyan')}")
                print(f"Timestamp: {tx.get('timestamp', 'N/A')}")
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
        bcdb = database.BlockChainDB()
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
        bcdb = database.BlockChainDB()
        chain = bcdb.find_all()

        if index == -1:
            index = len(chain) - 1

        if index < 0 or index >= len(chain):
            print(colored(f"Block not found. Valid range: 0-{len(chain)-1}", "red"))
            return

        block = chain[index]
        print(colored(f"\n=== Block #{block['index']} ===", "cyan", bold=True))
        print(f"Timestamp:   {block['timestamp']} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block['timestamp']))})")
        print(f"Hash:        {colored(block.get('hash', 'N/A'), 'white')}")
        print(f"Prev Hash:   {colored(block.get('previous_block', 'N/A'), 'white')}")
        print(f"Difficulty:  {colored(str(block.get('difficulty', 5)), 'cyan')} ({block.get('difficulty', 5)} leading zeros)")
        print(f"Nonce:       {block.get('nouce', 'N/A')}")
        print(f"Transactions: {colored(str(len(block.get('tx', []))), 'green')}")
        for i, tx_hash in enumerate(block.get('tx', [])):
            print(f"  {i+1}. {tx_hash[:40]}...")

    def chain_info(self):
        bcdb = database.BlockChainDB()
        chain = bcdb.find_all()

        if not chain:
            print(colored("No blocks in chain", "yellow"))
            return

        difficulties = [b.get('difficulty', 5) for b in chain]
        nonces = [b.get('nouce', 0) for b in chain]

        print(colored("\n=== Chain Info ===", "cyan", bold=True))
        print(f"Total blocks:      {colored(str(len(chain)), 'green')}")
        print(f"Genesis block:     {colored(chain[0]['hash'][:20] + '...', 'white')}")
        print(f"Latest block:      {colored(chain[-1]['hash'][:20] + '...', 'white')}")
        print(f"Current difficulty: {colored(str(difficulties[-1]), 'cyan')}")
        print(f"Difficulty range:  {min(difficulties)} - {max(difficulties)}")
        print(f"Average nonce:     {sum(nonces) // len(nonces):,}")

        if len(chain) >= 10:
            recent_diffs = [chain[i+1]['timestamp'] - chain[i]['timestamp']
                           for i in range(len(chain)-10, len(chain)-1)]
            print(f"Last 10 avg time:  {sum(recent_diffs) // len(recent_diffs)}s")

    def chain_verify(self):
        bcdb = database.BlockChainDB()
        chain = bcdb.find_all()

        print(colored("\n=== Verifying Chain ===", "cyan", bold=True))

        if not chain:
            print(colored("No blocks to verify", "yellow"))
            return

        errors = []
        for i in range(len(chain)):
            block = chain[i]

            if block['index'] != i:
                errors.append(f"Block {i}: Invalid index (expected {i}, got {block['index']})")

            if i > 0:
                if block.get('previous_block') != chain[i-1].get('hash'):
                    errors.append(f"Block {i}: Previous hash mismatch")

            test_block = block_module.Block(block['index'], block['timestamp'], block['tx'],
                             block.get('previous_block', ''), block.get('difficulty', 5))
            nonce = block.get('nouce', 0)
            if not test_block.valid(nonce):
                errors.append(f"Block {i}: Invalid proof of work")

        if errors:
            print(colored(f"\nVerification FAILED! {len(errors)} errors:", "red", bold=True))
            for error in errors:
                print(colored(f"  - {error}", "red"))
        else:
            print(colored(f"\nVerification PASSED! {len(chain)} blocks valid.", "green", bold=True))

    def cmd_pending(self, args):
        self.tx_pending()


def main():
    cli = BlockchainCLI()
    cli.start()


if __name__ == '__main__':
    main()
