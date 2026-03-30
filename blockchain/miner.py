# coding:utf-8
from blockchain.block import Block
import time
from blockchain.transaction import Vout, Transaction, MIN_FEE, validate_transaction
from blockchain.account import get_account, get_unlocked_account
from blockchain.database import BlockChainDB, TransactionDB, UnTransactionDB
from blockchain.config import MINING_REWARD
from blockchain.exceptions import WalletLockedError, ValidationError

MAX_COIN = 21000000
REWARD = MINING_REWARD


def calculate_total_fees(transactions):
    return sum(tx.get('fee', MIN_FEE) for tx in transactions)


def reward_with_fees(total_fees, private_key=None):
    account = get_account()
    if not account:
        raise WalletLockedError("No wallet found. Create or login to an account first.")
    
    reward_amount = REWARD + total_fees
    return Vout(account['address'], reward_amount)


def validate_pending_transactions(untxs):
    validated_txs = []
    invalid_txs = []
    
    for tx in untxs:
        try:
            validate_transaction(tx, require_signature=True)
            validated_txs.append(tx)
        except ValidationError as e:
            invalid_txs.append((tx.get('hash', 'unknown')[:20], str(e)))
    
    return validated_txs, invalid_txs


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
    
    valid_txs, invalid_txs = validate_pending_transactions(untxs)
    
    if invalid_txs:
        for tx_hash, error in invalid_txs:
            print(f"Warning: Skipping invalid transaction {tx_hash}...: {error}")
        untxdb.clear()
        for tx in valid_txs:
            untxdb.insert(tx)
    
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
