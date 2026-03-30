# coding:utf-8
import argparse
import sys
import time
import threading
import getpass
from datetime import datetime

from lib.common import colored, cprint

from blockchain import node, miner, account as account_module, transaction
from blockchain import database as db_module
from blockchain import block as block_module
from blockchain.miner import REWARD
from blockchain.exceptions import (
    ValidationError, DoubleSpendError, InvalidAddressError,
    InsufficientFundsError, AmountError, UTXONotFoundError,
    WalletLockedError, InvalidPasswordError
)


def get_balance(address):
    unspent = transaction.Vout.get_unspent(address)
    return sum(vout.amount for vout in unspent)


def register_commands(subparsers):
    wallet_parser = subparsers.add_parser('wallet', help='Wallet management')
    wallet_sub = wallet_parser.add_subparsers(dest='wallet_cmd', required=True)

    w_new = wallet_sub.add_parser('new', help='Create new wallet')
    w_new.add_argument('password', help='Password to encrypt wallet')
    w_new.set_defaults(func=cmd_wallet_new)

    wallet_sub.add_parser('list', help='List all accounts').set_defaults(func=cmd_wallet_list)
    wallet_sub.add_parser('address', help='Show current address').set_defaults(func=cmd_wallet_address)
    wallet_sub.add_parser('balance', help='Show balance').set_defaults(func=cmd_wallet_balance)

    w_login = wallet_sub.add_parser('login', help='Switch account')
    w_login.add_argument('index', type=int, help='Account index')
    w_login.set_defaults(func=cmd_wallet_login)

    wallet_sub.add_parser('logout', help='Logout from current account').set_defaults(func=cmd_wallet_logout)

    send_parser = subparsers.add_parser('send', help='Send coins')
    send_parser.add_argument('to', help='Recipient address')
    send_parser.add_argument('amount', type=int, help='Amount to send')
    send_parser.add_argument('password', help='Wallet password')
    send_parser.set_defaults(func=cmd_send)

    mine_parser = subparsers.add_parser('mine', help='Mining control')
    mine_sub = mine_parser.add_subparsers(dest='mine_cmd', required=True)
    mine_sub.add_parser('start', help='Start mining').set_defaults(func=cmd_mine_start)
    mine_sub.add_parser('stop', help='Stop mining').set_defaults(func=cmd_mine_stop)

    node_parser = subparsers.add_parser('node', help='Node management')
    node_sub = node_parser.add_subparsers(dest='node_cmd', required=True)

    n_connect = node_sub.add_parser('connect', help='Add peer node')
    n_connect.add_argument('address', help='Node address (host:port)')
    n_connect.set_defaults(func=cmd_node_connect)

    node_sub.add_parser('list', help='List connected nodes').set_defaults(func=cmd_node_list)
    node_sub.add_parser('discover', help='Discover nodes via mDNS').set_defaults(func=cmd_node_discover)

    n_status = node_sub.add_parser('status', help='Show node status')
    n_status.set_defaults(func=cmd_node_status)

    chain_parser = subparsers.add_parser('chain', help='Blockchain queries')
    chain_sub = chain_parser.add_subparsers(dest='chain_cmd', required=True)

    chain_sub.add_parser('status', help='Chain statistics').set_defaults(func=cmd_chain_status)
    chain_sub.add_parser('verify', help='Verify chain integrity').set_defaults(func=cmd_chain_verify)

    c_block = chain_sub.add_parser('block', help='View block details')
    c_block.add_argument('index', type=int, help='Block index')
    c_block.set_defaults(func=cmd_chain_block)

    c_tx = chain_sub.add_parser('tx', help='View transaction')
    c_tx.add_argument('hash', help='Transaction hash')
    c_tx.set_defaults(func=cmd_chain_tx)

    subparsers.add_parser('status', help='Quick status summary').set_defaults(func=cmd_status)
    subparsers.add_parser('pending', help='List pending transactions').set_defaults(func=cmd_pending)

    return subparsers


def cmd_wallet_new(args):
    password = args.password
    
    print(colored("\nCreating new wallet...", "cyan"))
    
    private_key, public_key, address = account_module.new_account(password)
    
    print(colored("\n=== New Wallet Created ===", "green", bold=True))
    print(f"Address: {colored(address, 'cyan', bold=True)}")
    print(colored("\nWallet encrypted and saved securely.", "green"))
    print(colored("You will need your password to send transactions.", "yellow"))


def cmd_wallet_list(args):
    accounts = account_module.get_accounts()
    print(colored("\n=== All Accounts ===", "cyan", bold=True))
    
    if accounts:
        for i, acc in enumerate(accounts, 1):
            balance = get_balance(acc['address'])
            active_marker = colored(" <-- active", "green", bold=True) if acc.get('is_active') else ""
            print(f"\n{i}. {colored(acc['address'][:30] + '...', 'cyan')}{active_marker}")
            print(f"   Balance: {colored(str(balance), 'green')} coins")
    else:
        print(colored("No accounts found", "yellow"))
    
    print(colored("\n  Use 'wallet login <index>' to switch accounts", "dim"))


def cmd_wallet_address(args):
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
        print(colored("No account found. Create one with 'wallet new <password>'", "yellow"))


def cmd_wallet_balance(args):
    account = account_module.get_account()
    if not account:
        print(colored("No account found. Create one with 'wallet new <password>'", "yellow"))
        return

    balance = get_balance(account['address'])
    print(colored("\n=== Balance ===", "cyan", bold=True))
    print(f"Address: {colored(account['address'], 'white')}")
    print(f"Balance: {colored(str(balance), 'green', bold=True)} coins")


def cmd_wallet_login(args):
    index = args.index
    
    accounts = account_module.get_accounts()
    if index < 1 or index > len(accounts):
        print(colored(f"Invalid index. Available: 1-{len(accounts)}", "red"))
        return
    
    if account_module.login(index):
        account = accounts[index - 1]
        print(colored(f"\nLogged in to account {index}", "green", bold=True))
        print(f"Address: {colored(account['address'], 'cyan')}")
        if account.get('encrypted_key'):
            print(colored("\nNote: Provide password to unlock for transactions", "yellow"))
    else:
        print(colored("Login failed", "red"))


def cmd_wallet_logout(args):
    account = account_module.get_account()
    if not account:
        print(colored("No account is currently logged in", "yellow"))
        return
    
    account_module.logout()
    print(colored("Logged out successfully", "green"))


def cmd_send(args):
    account = account_module.get_account()
    if not account:
        print(colored("No account found. Create one with 'wallet new <password>'", "yellow"))
        return

    from_address = account['address']
    to_address = args.to
    amount = args.amount
    password = args.password
    balance = get_balance(from_address)

    print(colored(f"\nSending {amount} coins to {to_address}...", "cyan"))
    print(f"From: {colored(from_address, 'white')}")
    print(f"To:   {colored(to_address, 'white')}")
    print(f"Amount: {colored(str(amount), 'green')} coins")
    print(f"Balance: {colored(str(balance), 'yellow')} coins")

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


def cmd_mine_start(args):
    print(colored("\n=== Starting Mining ===", "cyan", bold=True))
    print(colored("Press Ctrl+C to stop\n", "yellow"))
    
    mining_state = {'running': True}
    
    def mining_loop():
        while mining_state['running']:
            try:
                print(colored(f"[{time.strftime('%H:%M:%S')}] ", "dim") + "Mining block...", end="\r")
                block = miner.mine()
                print(colored(f"[{time.strftime('%H:%M:%S')}] ", "dim") +
                      colored(f"Block #{block.index} ", "green", bold=True) +
                      f"mined! (nonce={block.nouce}, diff={block.difficulty})")
                time.sleep(1)
            except KeyboardInterrupt:
                mining_state['running'] = False
                break
            except Exception as e:
                if mining_state['running']:
                    print(colored(f"\nMining error: {e}", "red"))
                    time.sleep(5)
    
    mining_state['thread'] = threading.Thread(target=mining_loop, daemon=True)
    mining_state['thread'].start()
    
    try:
        while mining_state['running'] and mining_state['thread'].is_alive():
            mining_state['thread'].join(timeout=1)
    except KeyboardInterrupt:
        mining_state['running'] = False
        print(colored("\nMining stopped", "yellow"))


def cmd_mine_stop(args):
    print(colored("Mining stop requested (not implemented for one-shot commands)", "yellow"))


def cmd_node_connect(args):
    address = args.address
    if '://' not in address:
        address = 'http://' + address
    node.add_node(address)
    print(colored(f"Added node: {address}", "green"))


def cmd_node_list(args):
    nodes = node.get_nodes_status()
    print(colored("\n=== Connected Nodes ===", "cyan", bold=True))
    
    if nodes:
        for i, n in enumerate(nodes, 1):
            status_color = 'green' if n['is_alive'] else 'red'
            status_text = 'ONLINE' if n['is_alive'] else 'OFFLINE'
            last_seen = n['last_seen']
            if last_seen > 0:
                last_seen_str = datetime.fromtimestamp(last_seen).strftime('%H:%M:%S')
            else:
                last_seen_str = 'Never'
            print(f"\n  {i}. {colored(n['address'], 'cyan')}")
            print(f"     Status: {colored(status_text, status_color)}")
            print(f"     Last seen: {colored(last_seen_str, 'yellow')}")
    else:
        print(colored("  No nodes configured", "yellow"))


def cmd_node_discover(args):
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


def cmd_node_status(args):
    status = node.get_node_status()
    if not isinstance(status, list):
        status = [status] if status else []
    
    print(colored("\n=== Node Status ===", "cyan", bold=True))
    alive = sum(1 for n in status if n.get('is_alive', False))
    total = len(status)
    print(f"  Total nodes: {colored(str(total), 'white')}")
    print(f"  Online: {colored(str(alive), 'green')}")
    print(f"  Offline: {colored(str(total - alive), 'red')}")


def cmd_chain_status(args):
    bcdb = db_module.BlockChainDB()
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


def cmd_chain_block(args):
    bcdb = db_module.BlockChainDB()
    chain = bcdb.find_all()
    index = args.index

    if index < 0 or index >= len(chain):
        print(colored(f"Block not found. Valid range: 0-{len(chain)-1}", "red"))
        return

    block = chain[index]
    fees = block.get('fees_collected', 0)
    miner_reward = REWARD + fees
    
    print(colored(f"\n=== Block #{block['index']} ===", "cyan", bold=True))
    print(f"Timestamp:    {block['timestamp']} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block['timestamp']))})")
    print(f"Hash:         {colored(block.get('hash', 'N/A'), 'white')}")
    print(f"Prev Hash:    {colored(block.get('previous_block', 'N/A'), 'white')}")
    print(f"Difficulty:   {colored(str(block.get('difficulty', 5)), 'cyan')} ({block.get('difficulty', 5)} leading zeros)")
    print(f"Nonce:        {block.get('nouce', 'N/A')}")
    print(f"Fees:         {colored(str(fees), 'yellow')} coins")
    print(f"Miner reward: {colored(str(miner_reward), 'green')} coins ({REWARD} base + {fees} fees)")
    print(f"Transactions: {colored(str(len(block.get('tx', []))), 'green')}")
    
    for i, tx_hash in enumerate(block.get('tx', [])):
        print(f"  {i+1}. {tx_hash[:40]}...")


def cmd_chain_tx(args):
    txdb = db_module.TransactionDB()
    untxdb = db_module.UnTransactionDB()
    tx_hash = args.hash

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


def cmd_chain_verify(args):
    bcdb = db_module.BlockChainDB()
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


def cmd_status(args):
    bcdb = db_module.BlockChainDB()
    chain = bcdb.find_all()
    txdb = db_module.TransactionDB()
    transactions = txdb.find_all()
    untxdb = db_module.UnTransactionDB()
    pending = untxdb.find_all()

    account = account_module.get_account()
    balance = get_balance(account['address']) if account else 0

    node_status = node.get_node_status()
    if not isinstance(node_status, list):
        node_status = [node_status] if node_status else []
    alive_nodes = sum(1 for n in node_status if n.get('is_alive', False))

    total_fees = sum(b.get('fees_collected', 0) for b in chain)

    print(colored("\n=== Blockchain Status ===", "cyan", bold=True))
    print(f"Blocks:       {colored(str(len(chain)), 'green')}")
    print(f"Tx Confirmed: {colored(str(len(transactions)), 'green')}")
    print(f"Tx Pending:   {colored(str(len(pending)), 'yellow')}")
    print(f"Nodes:        {colored(str(alive_nodes), 'cyan')}")
    print(f"Balance:      {colored(str(balance), 'green')} coins")
    
    if account:
        print(f"Address:      {colored(account['address'][:20] + '...', 'white')}")


def cmd_pending(args):
    untxdb = db_module.UnTransactionDB()
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
