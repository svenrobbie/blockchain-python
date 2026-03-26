# coding:utf-8
import hashlib
import base64
from blockchain.model import Model
from lib.common import pubkey_to_address, hash160
from blockchain.database import AccountDB
from blockchain.exceptions import InvalidPasswordError, WalletLockedError

try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False


def _get_fernet_key(password):
    key = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(key)


def _encrypt_key(private_key, password):
    if not FERNET_AVAILABLE:
        return private_key
    key = _get_fernet_key(password)
    f = Fernet(key)
    return f.encrypt(private_key.encode()).decode()


def _decrypt_key(encrypted_key, password):
    if not FERNET_AVAILABLE or not encrypted_key:
        return encrypted_key
    try:
        key = _get_fernet_key(password)
        f = Fernet(key)
        return f.decrypt(encrypted_key.encode()).decode()
    except Exception:
        raise InvalidPasswordError("Invalid password")


def new_account(password=None):
    private_key = _generate_private_key()
    public_key = hash160(private_key.encode())
    address = pubkey_to_address(public_key.encode())
    
    encrypted_key = ""
    if password:
        encrypted_key = _encrypt_key(private_key, password)
    
    adb = AccountDB()
    adb.insert({
        'pubkey': public_key, 
        'address': address,
        'encrypted_key': encrypted_key
    })
    
    return private_key, public_key, address


def _generate_private_key():
    import os
    import time
    import random
    entropy = os.urandom(32) + str(random.randrange(2**256)).encode() + str(int(time.time() * 1000000)).encode()
    return hashlib.sha256(entropy).hexdigest()


def get_account():
    adb = AccountDB()
    return adb.find_one()


def get_accounts():
    adb = AccountDB()
    return adb.find_all()


def get_unlocked_account(password):
    adb = AccountDB()
    account = adb.find_one()
    
    if not account:
        return None
    
    if account.get('encrypted_key'):
        private_key = _decrypt_key(account['encrypted_key'], password)
        account['private_key'] = private_key
        account['unlocked'] = True
    else:
        account['unlocked'] = False
    
    return account


def unlock_account(address, password):
    adb = AccountDB()
    account = adb.find_by_address(address)
    
    if not account:
        return None
    
    if account.get('encrypted_key'):
        private_key = _decrypt_key(account['encrypted_key'], password)
        account['private_key'] = private_key
        account['unlocked'] = True
    else:
        account['unlocked'] = False
    
    return account


def login(index_or_address, password=None):
    adb = AccountDB()
    if isinstance(index_or_address, int):
        account = adb.find_by_index(index_or_address)
    else:
        account = adb.find_by_address(index_or_address)
    
    if account:
        adb.set_active(account['id'])
        
        if password and account.get('encrypted_key'):
            try:
                private_key = _decrypt_key(account['encrypted_key'], password)
                account['private_key'] = private_key
                account['unlocked'] = True
            except InvalidPasswordError:
                raise
        
        return True
    return False


def logout():
    adb = AccountDB()
    adb.clear_active()


def set_password(address, password):
    adb = AccountDB()
    account = adb.find_by_address(address)
    
    if not account:
        return False
    
    encrypted_key = _encrypt_key(account.get('private_key', ''), password)
    adb.update_encrypted_key(account['id'], encrypted_key)
    return True
