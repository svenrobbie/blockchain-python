# coding:utf-8
import time
import json
import hashlib
from blockchain.model import Model
from blockchain.database import TransactionDB, UnTransactionDB
from blockchain.rpc import BroadCast
from blockchain.exceptions import (
    WalletLockedError
)
from lib.common import is_valid_address, sign_data, hash160

MIN_FEE = 0.0001


class Vin(Model):
    def __init__(self, utxo_hash, amount, signature=None, pubkey=None):
        self.hash = utxo_hash
        self.amount = amount
        self.signature = signature
        self.pubkey = pubkey


class Vout(Model):
    def __init__(self, receiver, amount):
        if amount <= 0:
            raise AmountError("Output amount must be positive")
        
        if not isinstance(receiver, str):
            raise InvalidAddressError("Receiver must be a string")
        
        self.receiver = receiver
        self.amount = amount
        self.hash = hashlib.sha256((str(time.time()) + str(self.receiver) + str(self.amount)).encode('utf-8')).hexdigest()
    
    @classmethod
    def get_unspent(cls, addr):
        unspent = []
        all_tx = TransactionDB().find_all()
        spend_vin = []
        [spend_vin.extend(item['vin']) for item in all_tx]
        has_spend_hash = [vin['hash'] for vin in spend_vin]
        
        pending_tx = UnTransactionDB().find_all()
        pending_spend_hash = []
        for item in pending_tx:
            for vin_item in item.get('vin', []):
                pending_spend_hash.append(vin_item['hash'])
        
        for item in all_tx:
            for vout in item['vout']:
                if vout['receiver'] == addr and vout['hash'] not in has_spend_hash and vout['hash'] not in pending_spend_hash:
                    unspent.append(vout)
        return [Vin(tx['hash'], tx['amount']) for tx in unspent]


def check_double_spend(vin_list):
    pass


def check_utxo_exists(vin_list):
    pass


def validate_transaction_inputs(vin_list, from_addr, require_signature=True):
    pass


def validate_transaction_outputs(vout_list, total_input):
    pass


def validate_transaction(tx, require_signature=True):
    pass


class Transaction():
    def __init__(self, vin, vout):
        self.timestamp = int(time.time())
        self.vin = vin
        self.vout = vout
        self.hash = self.gen_hash()

    def gen_hash(self):
        return hashlib.sha256((str(self.timestamp) + str(self.vin) + str(self.vout)).encode('utf-8')).hexdigest()

    @classmethod
    def transfer(cls, from_addr, to_addr, amount, fee=MIN_FEE, private_key=None):
        if not is_valid_address(from_addr):
            raise InvalidAddressError(f"Invalid sender address: {from_addr[:20]}...")
        
        if not is_valid_address(to_addr):
            raise InvalidAddressError(f"Invalid recipient address: {to_addr[:20]}...")
        
        if from_addr == to_addr:
            raise InvalidAddressError("Cannot send to same address")
        
        if not isinstance(amount, (int, float)):
            amount = float(amount)
        
        if amount <= 0:
            raise AmountError("Amount must be positive")
        
        if not private_key:
            raise WalletLockedError("Wallet is locked. Please unlock with password first.")
        
        actual_fee = max(fee, MIN_FEE)
        total_needed = amount + actual_fee
        
        unspents = Vout.get_unspent(from_addr)
        ready_utxo, change = select_outputs_greedy(unspents, total_needed)
        
        if not ready_utxo:
            raise InsufficientFundsError(f"Insufficient funds (need {total_needed}, available {sum(u.amount for u in unspents)})")
        
        check_double_spend(ready_utxo)
        
        for utxo in ready_utxo:
            data_to_sign = f"{utxo.hash}:{utxo.amount}"
            signature = sign_data(data_to_sign, private_key)
            key_hash = hash160(private_key.encode())
            utxo.signature = signature
            utxo.pubkey = key_hash
        
        validate_transaction_inputs(ready_utxo, from_addr, require_signature=False)
        
        vin = ready_utxo
        vout = []
        vout.append(Vout(to_addr, amount))
        
        change_amount = change - actual_fee
        if change_amount > 0:
            vout.append(Vout(from_addr, change_amount))
        
        total_input = sum(v.amount for v in vin)
        validate_transaction_outputs(vout, total_input)
        
        tx = cls(vin, vout)
        tx_dict = tx.to_dict()
        tx_dict['fee'] = actual_fee
        UnTransactionDB().insert(tx_dict)
        return tx_dict

    @staticmethod
    def get_fee(tx):
        return tx.get('fee', MIN_FEE)

    @staticmethod
    def unblock_spread(untx):
        BroadCast().new_untransaction(untx)

    @staticmethod
    def blocked_spread(txs):
        BroadCast().blocked_transactions(txs)

    def to_dict(self):
        dt = self.__dict__
        if not isinstance(self.vin, list):
            self.vin = [self.vin]
        if not isinstance(self.vout, list):
            self.vout = [self.vout]
        dt['vin'] = [i.__dict__ for i in self.vin]
        dt['vout'] = [i.__dict__ for i in self.vout]
        return dt


def select_outputs_greedy(unspent, min_value): 
    if not unspent: 
        return None, 0 
    lessers = [utxo for utxo in unspent if utxo.amount < min_value] 
    greaters = [utxo for utxo in unspent if utxo.amount >= min_value] 
    key_func = lambda utxo: utxo.amount
    greaters.sort(key=key_func)
    if greaters: 
        min_greater = greaters[0]
        change = min_greater.amount - min_value 
        return [min_greater], change
    lessers.sort(key=key_func, reverse=True)
    result = []
    accum = 0
    for utxo in lessers: 
        result.append(utxo)
        accum += utxo.amount
        if accum >= min_value: 
            change = accum - min_value
            return result, change 
    return None, 0
