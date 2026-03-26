# coding:utf-8
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/api/node", tags=["node"])


@router.get("/status")
async def get_node_status():
    from database_sqlite import NodeDB, TransactionDB, BlockChainDB
    
    ndb = NodeDB()
    txdb = TransactionDB()
    bcdb = BlockChainDB()
    
    nodes = ndb.find_all()
    nodes_with_health = ndb.find_all_with_health()
    
    chain = bcdb.find_all()
    txs = txdb.find_all()
    
    alive_count = sum(1 for n in nodes_with_health if n.get("is_alive", False))
    
    return {
        "node_count": len(nodes),
        "alive_nodes": alive_count,
        "offline_nodes": len(nodes) - alive_count,
        "block_count": len(chain),
        "transaction_count": len(txs),
        "nodes": [
            {
                "address": n.get("address", ""),
                "is_alive": n.get("is_alive", False),
                "last_seen": n.get("last_seen", 0)
            }
            for n in nodes_with_health
        ]
    }


@router.get("/peers")
async def get_peers():
    from database_sqlite import NodeDB
    
    ndb = NodeDB()
    nodes = ndb.find_all_with_health()
    
    return {
        "peers": [
            {
                "address": n.get("address", ""),
                "status": "online" if n.get("is_alive", False) else "offline",
                "last_seen": n.get("last_seen", 0)
            }
            for n in nodes
        ]
    }


@router.post("/add")
async def add_peer(address: str):
    from node import add_node
    
    try:
        result = add_node(address)
        return {"success": True, "address": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/stats")
async def get_stats():
    from database_sqlite import BlockChainDB, TransactionDB, UnTransactionDB
    
    bcdb = BlockChainDB()
    txdb = TransactionDB()
    untxdb = UnTransactionDB()
    
    chain = bcdb.find_all()
    confirmed_txs = txdb.find_all()
    pending_txs = untxdb.find_all()
    
    total_fees = sum(b.get("fees_collected", 0) for b in chain)
    
    last_block = chain[-1] if chain else None
    
    return {
        "blocks": len(chain),
        "confirmed_transactions": len(confirmed_txs),
        "pending_transactions": len(pending_txs),
        "total_fees_collected": total_fees,
        "last_block": {
            "index": last_block["index"] if last_block else 0,
            "timestamp": last_block.get("timestamp", 0) if last_block else 0,
            "difficulty": last_block.get("difficulty", 5) if last_block else 5
        } if last_block else None
    }
