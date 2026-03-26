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
        return b

    @staticmethod
    def spread(block):
        BroadCast().new_block(block)