# coding:utf-8
from block import Block
import time
from transaction import Vout, Transaction, MIN_FEE
from account import get_account
from database_sqlite import BlockChainDB, TransactionDB, UnTransactionDB
from lib.common import unlock_sig, lock_sig

MAX_COIN = 21000000
REWARD = 20

def calculate_total_fees(transactions):
    """Calculate total fees from all transactions"""
    return sum(tx.get('fee', MIN_FEE) for tx in transactions)

def reward_with_fees(total_fees):
    """Create reward transaction with base reward + fees"""
    reward_amount = REWARD + total_fees
    return Vout(get_account()['address'], reward_amount)

def coinbase():
    """
    First block generate.
    """
    rw = reward_with_fees(0)
    tx = Transaction([], rw)
    tx_dict = tx.to_dict()
    tx_dict['fee'] = 0  # Coinbase has no fee
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
    """
    Main miner method.
    """
    last_block = BlockChainDB().last()
    if len(last_block) == 0:
        last_block = coinbase().to_dict()
    
    chain = BlockChainDB().find_all()
    difficulty = Block.calculate_difficulty(chain)
    
    untxdb = UnTransactionDB()
    untxs = untxdb.find_all()
    
    total_fees = calculate_total_fees(untxs)
    
    rw = reward_with_fees(total_fees)
    coinbase_tx = Transaction([], rw)
    coinbase_dict = coinbase_tx.to_dict()
    coinbase_dict['fee'] = 0
    
    untxs.append(coinbase_dict)
    untx_hashes = untxdb.all_hashes()
    untxdb.clear()
    
    untx_hashes.insert(0, coinbase_dict['hash'])
    cb = Block(last_block['index'] + 1, int(time.time()), untx_hashes, last_block['hash'], difficulty)
    cb.fees_collected = total_fees
    nouce = cb.pow()
    cb.make(nouce)
    BlockChainDB().insert(cb.to_dict())
    TransactionDB().insert(untxs)
    Block.spread(cb.to_dict())
    Transaction.blocked_spread(untxs)
    return cb