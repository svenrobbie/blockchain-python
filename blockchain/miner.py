# coding:utf-8
from blockchain.block import Block
import time
from blockchain.transaction import Vout, Transaction, MIN_FEE
from blockchain.account import get_account
from blockchain.database import BlockChainDB, TransactionDB, UnTransactionDB
from blockchain.exceptions import WalletLockedError

MAX_COIN = 21000000
REWARD = 2.5


def calculate_total_fees(transactions):
    return sum(tx.get('fee', MIN_FEE) for tx in transactions)


def reward_with_fees(total_fees, private_key=None):
    account = get_account()
    if not account:
        raise WalletLockedError("No wallet found. Create or login to an account first.")
    
    reward_amount = REWARD + total_fees
    return Vout(account['address'], reward_amount)


def validate_pending_transactions(untxs):
    return untxs, []


def coinbase():
    rw = reward_with_fees(0)
    tx = Transaction([], rw)
    tx_dict = tx.to_dict()
    tx_dict['fee'] = 0
    cb = Block(0, int(time.time()), [tx_dict['hash']], "", difficulty=5)
    cb.fees_collected = 0
    nouce = cb.pow()
    cb.make(nouce)
    BlockChainDB().insert(cb.to_dict())
    TransactionDB().insert(tx_dict)
    return cb


def get_all_untransactions():
    UnTransactionDB().all_hashes()


def mine():
    last_block = BlockChainDB().last()
    if len(last_block) == 0:
        last_block = coinbase().to_dict()
    
    chain = BlockChainDB().find_all()
    difficulty = Block.calculate_difficulty(chain)
    
    untxdb = UnTransactionDB()
    untxs = untxdb.find_all()
    
    valid_txs = untxs
    
    if not valid_txs:
        print("No valid transactions to mine (only coinbase)")
    
    total_fees = calculate_total_fees(valid_txs)
    
    rw = reward_with_fees(total_fees)
    coinbase_tx = Transaction([], rw)
    coinbase_dict = coinbase_tx.to_dict()
    coinbase_dict['fee'] = 0
    
    tx_hashes = [tx['hash'] for tx in valid_txs]
    tx_hashes.insert(0, coinbase_dict['hash'])
    
    cb = Block(last_block['index'] + 1, int(time.time()), tx_hashes, last_block['hash'], difficulty)
    cb.fees_collected = total_fees
    nouce = cb.pow()
    cb.make(nouce)
    BlockChainDB().insert(cb.to_dict())
    
    all_txs_to_save = valid_txs + [coinbase_dict]
    TransactionDB().insert(all_txs_to_save)
    
    Block.spread(cb.to_dict())
    Transaction.blocked_spread(all_txs_to_save)
    return cb
