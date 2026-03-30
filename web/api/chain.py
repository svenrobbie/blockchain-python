# coding:utf-8
from . import _project_root  # noqa: F401 - ensures path is initialized

from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/api/chain", tags=["chain"])


@router.get("/status")
async def get_chain_status():
    from blockchain.database import BlockChainDB
    
    bcdb = BlockChainDB()
    chain = bcdb.find_all()
    
    if not chain:
        return {
            "block_count": 0,
            "total_fees": 0,
            "last_block": None
        }
    
    last_block = chain[-1]
    total_fees = sum(b.get("fees_collected", 0) for b in chain)
    
    return {
        "block_count": len(chain),
        "total_fees": total_fees,
        "last_block": {
            "index": last_block["index"],
            "hash": last_block.get("hash", "")[:16] + "...",
            "timestamp": last_block.get("timestamp", 0),
            "difficulty": last_block.get("difficulty", 5),
            "tx_count": len(last_block.get("tx", []))
        }
    }


@router.get("/blocks")
async def get_blocks(limit: int = 10, offset: int = 0):
    from blockchain.database import BlockChainDB
    
    bcdb = BlockChainDB()
    chain = bcdb.find_all()
    
    total = len(chain)
    blocks = chain[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "blocks": [
            {
                "index": b["index"],
                "hash": b.get("hash", "")[:16] + "...",
                "timestamp": b.get("timestamp", 0),
                "difficulty": b.get("difficulty", 5),
                "tx_count": len(b.get("tx", [])),
                "fees": b.get("fees_collected", 0)
            }
            for b in reversed(blocks)
        ]
    }


@router.get("/block/{index}")
async def get_block(index: int):
    from blockchain.database import BlockChainDB
    
    bcdb = BlockChainDB()
    chain = bcdb.find_all()
    
    if index < 0 or index >= len(chain):
        return {"error": "Block not found"}
    
    block = chain[index]
    
    return {
        "index": block["index"],
        "hash": block.get("hash", ""),
        "previous_hash": block.get("previous_block", ""),
        "timestamp": block.get("timestamp", 0),
        "difficulty": block.get("difficulty", 5),
        "nonce": block.get("nouce", 0),
        "tx_count": len(block.get("tx", [])),
        "tx_hashes": block.get("tx", []),
        "fees_collected": block.get("fees_collected", 0)
    }


@router.get("/transactions")
async def get_transactions(limit: int = 20, offset: int = 0):
    from blockchain.database import TransactionDB
    
    txdb = TransactionDB()
    txs = txdb.find_all()
    
    total = len(txs)
    transactions = txs[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "transactions": [
            {
                "hash": tx.get("hash", "")[:20] + "...",
                "full_hash": tx.get("hash", ""),
                "timestamp": tx.get("timestamp", 0),
                "fee": tx.get("fee", 1),
                "vin_count": len(tx.get("vin", [])),
                "vout_count": len(tx.get("vout", []))
            }
            for tx in reversed(transactions)
        ]
    }


@router.get("/transaction/{tx_hash}")
async def get_transaction(tx_hash: str):
    from blockchain.database import TransactionDB, UnTransactionDB
    
    txdb = TransactionDB()
    untxdb = UnTransactionDB()
    
    all_txs = txdb.find_all() + untxdb.find_all()
    
    for tx in all_txs:
        if tx.get("hash") == tx_hash:
            return {
                "hash": tx.get("hash", ""),
                "timestamp": tx.get("timestamp", 0),
                "fee": tx.get("fee", 1),
                "status": "confirmed" if tx in txdb.find_all() else "pending",
                "vin": tx.get("vin", []),
                "vout": tx.get("vout", [])
            }
    
    return {"error": "Transaction not found"}


@router.get("/pending")
async def get_pending_transactions():
    from blockchain.database import UnTransactionDB
    
    untxdb = UnTransactionDB()
    pending = untxdb.find_all()
    
    return {
        "count": len(pending),
        "transactions": [
            {
                "hash": tx.get("hash", "")[:20] + "...",
                "full_hash": tx.get("hash", ""),
                "timestamp": tx.get("timestamp", 0),
                "fee": tx.get("fee", 1)
            }
            for tx in pending
        ]
    }


@router.get("/address/{address}")
async def get_address_transactions(address: str):
    from blockchain.database import TransactionDB, UnTransactionDB
    
    txdb = TransactionDB()
    untxdb = UnTransactionDB()
    
    all_txs = txdb.find_all() + untxdb.find_all()
    
    address_txs = []
    
    for tx in all_txs:
        is_relevant = False
        direction = None
        amount = 0
        
        for vout in tx.get("vout", []):
            if vout.get("receiver") == address:
                is_relevant = True
                direction = "received"
                amount += vout.get("amount", 0)
        
        for vin in tx.get("vin", []):
            pass
        
        if is_relevant:
            address_txs.append({
                "hash": tx.get("hash", "")[:20] + "...",
                "full_hash": tx.get("hash", ""),
                "direction": direction,
                "amount": amount,
                "timestamp": tx.get("timestamp", 0),
                "fee": tx.get("fee", 1),
                "status": "confirmed" if tx in txdb.find_all() else "pending"
            })
    
    return {
        "address": address,
        "transaction_count": len(address_txs),
        "transactions": address_txs
    }
