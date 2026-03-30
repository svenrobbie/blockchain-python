# coding:utf-8
from . import _project_root  # noqa: F401 - ensures path is initialized

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import hashlib
import base64

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


class CreateWalletRequest(BaseModel):
    password_hash: str
    salt: str


class SendRequest(BaseModel):
    from_address: str
    to_address: str
    amount: float
    password_hash: str


@router.get("/accounts")
async def get_accounts():
    from blockchain.account import get_accounts
    
    accounts = get_accounts()
    return {
        "accounts": [
            {
                "id": acc.get("id"),
                "address": acc.get("address"),
                "is_active": acc.get("is_active", False),
                "has_password": bool(acc.get("password_hash")),
                "salt": acc.get("salt", "") if acc.get("password_hash") else None
            }
            for acc in accounts
        ]
    }


@router.get("/account")
async def get_current_account():
    from blockchain.account import get_account
    
    account = get_account()
    if not account:
        return {"account": None}
    
    return {
        "account": {
            "id": account.get("id"),
            "address": account.get("address"),
            "is_active": account.get("is_active", False),
            "has_password": bool(account.get("password_hash")),
            "salt": account.get("salt", "") if account.get("password_hash") else None
        }
    }


@router.get("/balance/{address}")
async def get_balance(address: str):
    from blockchain.transaction import Vout
    
    unspent = Vout.get_unspent(address)
    balance = sum(vout.amount for vout in unspent)
    return {"address": address, "balance": balance}


@router.get("/balance")
async def get_current_balance():
    from blockchain.account import get_account
    from blockchain.transaction import Vout
    
    account = get_account()
    if not account:
        return {"balance": 0, "address": None}
    
    unspent = Vout.get_unspent(account["address"])
    balance = sum(vout.amount for vout in unspent)
    return {"address": account["address"], "balance": balance}


@router.post("/create")
async def create_wallet(request: CreateWalletRequest):
    from blockchain.account import new_account
    
    try:
        private_key, public_key, address = new_account(
            password=None,
            password_hash=request.password_hash,
            salt=request.salt
        )
        return {
            "success": True,
            "address": address,
            "message": "Wallet created successfully!"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/send")
async def send_coins(request: SendRequest):
    from blockchain.transaction import Transaction
    from blockchain.database import AccountDB
    from blockchain.account import verify_password_hash, _decrypt_key
    from blockchain.exceptions import (
        ValidationError, DoubleSpendError, InvalidAddressError,
        InsufficientFundsError, AmountError, UTXONotFoundError,
        WalletLockedError
    )
    
    adb = AccountDB()
    account = adb.find_by_address(request.from_address)
    
    if not account:
        return {"success": False, "error": "Account not found"}
    
    stored_hash = account.get("password_hash")
    salt = account.get("salt")
    
    if not stored_hash or not salt:
        return {"success": False, "error": "Wallet has no password set"}
    
    if not verify_password_hash(request.password_hash, salt, stored_hash):
        return {"success": False, "error": "Invalid password"}
    
    try:
        private_key = _decrypt_key(account.get("encrypted_key", ""), "dummy_for_hash_verified")
    except Exception:
        private_key = None
    
    if not private_key:
        return {"success": False, "error": "Failed to decrypt private key"}
    
    try:
        tx_dict = Transaction.transfer(
            request.from_address,
            request.to_address,
            request.amount,
            private_key=private_key
        )
        
        Transaction.unblock_spread(tx_dict)
        
        return {
            "success": True,
            "tx_hash": tx_dict["hash"],
            "amount": request.amount,
            "to": request.to_address
        }
    except WalletLockedError as e:
        return {"success": False, "error": "Wallet is locked. " + str(e)}
    except InsufficientFundsError as e:
        return {"success": False, "error": "Insufficient funds. " + str(e)}
    except InvalidAddressError as e:
        return {"success": False, "error": "Invalid address. " + str(e)}
    except DoubleSpendError as e:
        return {"success": False, "error": "Double spend detected. " + str(e)}
    except AmountError as e:
        return {"success": False, "error": "Invalid amount. " + str(e)}
    except UTXONotFoundError as e:
        return {"success": False, "error": "UTXO not found. " + str(e)}
    except ValidationError as e:
        return {"success": False, "error": "Validation error. " + str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/login/{index}")
async def login_account(index: int):
    from blockchain.account import login, get_accounts
    
    accounts = get_accounts()
    if index < 1 or index > len(accounts):
        return {"success": False, "error": "Invalid account index"}
    
    success = login(index)
    if success:
        return {"success": True, "address": accounts[index - 1]["address"]}
    return {"success": False, "error": "Login failed"}


@router.post("/logout")
async def logout_account():
    from blockchain.account import logout
    
    logout()
    return {"success": True}
