# coding:utf-8
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter
import threading
import time

router = APIRouter(prefix="/api/mine", tags=["mining"])

mining_state = {
    'is_mining': False,
    'thread': None,
    'blocks_mined': 0,
    'total_earnings': 0,
    'current_block_index': 0,
    'current_nonce': 0,
    'start_time': None
}


def mining_loop():
    from blockchain import miner
    from blockchain.database import BlockChainDB
    
    bcdb = BlockChainDB()
    last_block_count = len(bcdb.find_all())
    
    while mining_state['is_mining']:
        try:
            chain = bcdb.find_all()
            mining_state['current_block_index'] = len(chain)
            
            block = miner.mine()
            
            mining_state['blocks_mined'] += 1
            mining_state['total_earnings'] += 20 + block.fees_collected
            
            mining_state['current_block_index'] = block.index + 1
            
        except Exception as e:
            print(f"Mining error: {e}")
            time.sleep(1)
        
        if not mining_state['is_mining']:
            break
    
    mining_state['is_mining'] = False


@router.get("/status")
async def get_mining_status():
    return {
        "is_mining": mining_state['is_mining'],
        "blocks_mined": mining_state['blocks_mined'],
        "total_earnings": mining_state['total_earnings'],
        "current_block_index": mining_state['current_block_index'],
        "start_time": mining_state['start_time']
    }


@router.post("/start")
async def start_mining():
    if mining_state['is_mining']:
        return {"success": True, "message": "Mining already running"}
    
    mining_state['is_mining'] = True
    mining_state['thread'] = threading.Thread(target=mining_loop, daemon=True)
    mining_state['thread'].start()
    mining_state['start_time'] = int(time.time())
    
    return {"success": True, "message": "Mining started"}


@router.post("/stop")
async def stop_mining():
    if not mining_state['is_mining']:
        return {"success": True, "message": "Mining not running"}
    
    mining_state['is_mining'] = False
    
    if mining_state['thread']:
        mining_state['thread'].join(timeout=5)
    
    return {
        "success": True,
        "message": "Mining stopped",
        "blocks_mined": mining_state['blocks_mined'],
        "total_earnings": mining_state['total_earnings']
    }
