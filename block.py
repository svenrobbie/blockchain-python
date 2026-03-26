# coding:utf-8
import hashlib
import time
from model import Model
from rpc import BroadCast

class Block(Model):

    MIN_DIFFICULTY = 2
    MAX_DIFFICULTY = 5
    TARGET_TIME = 60
    ADJUSTMENT_WINDOW = 10

    def __init__(self, index, timestamp, tx, previous_hash, difficulty=5):
        self.index = index
        self.timestamp = timestamp
        self.tx = tx
        self.previous_block = previous_hash
        self.difficulty = difficulty
        self.fees_collected = 0

    def header_hash(self):
        """
        Refer to bitcoin block header hash
        """          
        return hashlib.sha256((str(self.index) + str(self.timestamp) + str(self.tx) + str(self.previous_block)).encode('utf-8')).hexdigest()

    def pow(self):
        """
        Proof of work. Add nouce to block.
        """        
        nouce = 0
        while self.valid(nouce) is False:
            nouce += 1
        self.nouce = nouce
        return nouce

    def make(self, nouce):
        """
        Block hash generate. Add hash to block.
        """
        self.hash = self.ghash(nouce)
    
    def ghash(self, nouce):
        """
        Block hash generate.
        """        
        header_hash = self.header_hash()
        token = ''.join((header_hash, str(nouce))).encode('utf-8')
        return hashlib.sha256(token).hexdigest()

    def valid(self, nouce):
        """
        Validates the Proof using dynamic difficulty
        """
        return self.ghash(nouce)[:self.difficulty] == "0" * self.difficulty

    @staticmethod
    def calculate_difficulty(chain):
        """
        Calculate difficulty for next block based on recent blocks.
        Uses ADJUSTMENT_WINDOW blocks to calculate average time.
        """
        if len(chain) < Block.ADJUSTMENT_WINDOW:
            if len(chain) == 0:
                return 5
            return chain[-1].get('difficulty', 5)

        recent = chain[-Block.ADJUSTMENT_WINDOW:]
        time_diff = recent[-1]['timestamp'] - recent[0]['timestamp']
        expected_time = Block.ADJUSTMENT_WINDOW * Block.TARGET_TIME

        avg_time = time_diff / Block.ADJUSTMENT_WINDOW
        last_difficulty = chain[-1].get('difficulty', 5)

        if avg_time < Block.TARGET_TIME * 0.8:
            return min(last_difficulty + 1, Block.MAX_DIFFICULTY)
        elif avg_time > Block.TARGET_TIME * 1.2:
            return max(last_difficulty - 1, Block.MIN_DIFFICULTY)
        return last_difficulty

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, bdict):
        b = cls(bdict['index'], bdict['timestamp'], bdict['tx'], bdict['previous_block'],
                bdict.get('difficulty', 5))
        b.hash = bdict['hash']
        b.nouce = bdict['nouce']
        b.fees_collected = bdict.get('fees_collected', 0)
        return b

    @staticmethod
    def spread(block):
        BroadCast().new_block(block)

    @staticmethod
    def validate_block_structure(block):
        if not isinstance(block, dict):
            return False, "Block must be a dictionary"
        
        required_fields = ['index', 'timestamp', 'tx', 'previous_block', 'difficulty', 'hash', 'nouce']
        for field in required_fields:
            if field not in block:
                return False, f"Missing required field: {field}"
        
        if block['index'] < 0:
            return False, "Invalid block index"
        
        if not isinstance(block['timestamp'], (int, float)):
            return False, "Invalid timestamp"
        
        current_time = int(time.time())
        if block['timestamp'] > current_time + 3600:
            return False, "Block timestamp too far in future"
        
        if block['timestamp'] < 0:
            return False, "Block timestamp cannot be negative"
        
        if block['difficulty'] < Block.MIN_DIFFICULTY or block['difficulty'] > Block.MAX_DIFFICULTY:
            return False, f"Difficulty out of range ({Block.MIN_DIFFICULTY}-{Block.MAX_DIFFICULTY})"
        
        return True, ""

    @staticmethod
    def validate_pow(block):
        if isinstance(block, dict):
            hash_value = block.get('hash', '')
            difficulty = block.get('difficulty', 5)
            nonce = block.get('nouce', 0)
            index = block.get('index', 0)
            timestamp = block.get('timestamp', 0)
            tx = block.get('tx', [])
            previous_hash = block.get('previous_block', '')
        else:
            hash_value = block.hash
            difficulty = block.difficulty
            nonce = block.nouce
            index = block.index
            timestamp = block.timestamp
            tx = block.tx
            previous_hash = block.previous_block
        
        expected_prefix = "0" * difficulty
        if not hash_value.startswith(expected_prefix):
            return False, f"Invalid PoW: hash doesn't start with {expected_prefix}"
        
        return True, ""

    @staticmethod
    def validate(block_dict, previous_block=None, require_signatures=True):
        valid, error = Block.validate_block_structure(block_dict)
        if not valid:
            return False, error
        
        valid, error = Block.validate_pow(block_dict)
        if not valid:
            return False, error
        
        if previous_block is not None:
            if block_dict['index'] != previous_block['index'] + 1:
                return False, f"Invalid block index (expected {previous_block['index'] + 1}, got {block_dict['index']})"
            
            if block_dict['previous_block'] != previous_block['hash']:
                return False, "Previous hash mismatch"
        
        return True, ""