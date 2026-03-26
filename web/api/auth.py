# coding:utf-8
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import hashlib
import base64

router = APIRouter(prefix="/api/auth", tags=["auth"])

try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False


def get_fernet_key(password):
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)


def decrypt_key(encrypted_key, password):
    if not FERNET_AVAILABLE or not encrypted_key:
        return encrypted_key
    try:
        key = get_fernet_key(password)
        f = Fernet(key)
        return f.decrypt(encrypted_key.encode()).decode()
    except Exception:
        return None


class PasswordVerifyRequest(BaseModel):
    address: str
    password: str


@router.post("/verify")
async def verify_password(request: PasswordVerifyRequest):
    from blockchain.database import AccountDB
    
    adb = AccountDB()
    account = adb.find_by_address(request.address)
    
    if not account:
        return {"valid": False, "error": "Account not found"}
    
    if not account.get('encrypted_key'):
        return {"valid": False, "error": "Wallet has no password set"}
    
    private_key = decrypt_key(account['encrypted_key'], request.password)
    
    if private_key:
        return {"valid": True}
    else:
        return {"valid": False, "error": "Invalid password"}


@router.post("/unlock")
async def unlock_wallet(request: PasswordVerifyRequest):
    from blockchain.database import AccountDB
    
    adb = AccountDB()
    account = adb.find_by_address(request.address)
    
    if not account:
        return {"success": False, "error": "Account not found"}
    
    if not account.get('encrypted_key'):
        return {"success": False, "error": "Wallet has no password set"}
    
    private_key = decrypt_key(account['encrypted_key'], request.password)
    
    if private_key:
        return {"success": True, "private_key": private_key}
    else:
        return {"success": False, "error": "Invalid password"}
