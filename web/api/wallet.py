# coding:utf-8
import sys
import os

web_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(web_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


class CreateWalletRequest(BaseModel):
    password: str


class SendRequest(BaseModel):
    from_address: str
    to_address: str
    amount: int
    password: str
    fee: float = 0.0001


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
                "has_password": bool(acc.get("encrypted_key"))
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
            "has_password": bool(account.get("encrypted_key"))
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
        private_key, public_key, address = new_account(request.password)
        return {
            "success": True,
            "address": address,
            "message": "Wallet created successfully. Remember your password!"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/send")
async def send_coins(request: SendRequest):
    from blockchain.transaction import Transaction
    from blockchain.database import AccountDB
    from blockchain.exceptions import (
        ValidationError, DoubleSpendError, InvalidAddressError,
        InsufficientFundsError, AmountError, UTXONotFoundError,
        WalletLockedError
    )
    import hashlib
    import base64
    
    try:
        from cryptography.fernet import Fernet
        FERNET_AVAILABLE = True
    except ImportError:
        FERNET_AVAILABLE = False
    
    def decrypt_key(encrypted_key, password):
        if not FERNET_AVAILABLE or not encrypted_key:
            return encrypted_key
        try:
            key = hashlib.sha256(password.encode()).digest()
            key_b64 = base64.urlsafe_b64encode(key)
            f = Fernet(key_b64)
            return f.decrypt(encrypted_key.encode()).decode()
        except Exception:
            return None
    
    adb = AccountDB()
    account = adb.find_by_address(request.from_address)
    
    if not account:
        return {"success": False, "error": "Account not found"}
    
    if not account.get("encrypted_key"):
        return {"success": False, "error": "Wallet has no password. Use CLI to set password first."}
    
    private_key = decrypt_key(account["encrypted_key"], request.password)
    if not private_key:
        return {"success": False, "error": "Invalid password"}
    
    try:
        tx_dict = Transaction.transfer(
            request.from_address,
            request.to_address,
            request.amount,
            fee=request.fee,
            private_key=private_key
        )
        
        Transaction.unblock_spread(tx_dict)
        
        return {
            "success": True,
            "tx_hash": tx_dict["hash"],
            "amount": request.amount,
            "fee": request.fee,
            "total": request.amount + request.fee,
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
