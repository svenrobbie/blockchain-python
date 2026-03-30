# coding:utf-8
import sqlite3
import json
import os
import time
from functools import wraps

_package_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(_package_dir, 'data', 'blockchain_v2.db')


def transaction(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        conn = self.get_conn()
        try:
            conn.execute("BEGIN")
            result = func(self, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise
    return wrapper


class SQLiteDB:
    _connection = None

    @classmethod
    def get_conn(cls):
        if cls._connection is None:
            db_dir = os.path.dirname(DATABASE_PATH)
            os.makedirs(db_dir, exist_ok=True)
            cls._connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            cls._connection.row_factory = sqlite3.Row
        return cls._connection

    @classmethod
    def init_db(cls):
        conn = cls.get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                block_index INTEGER UNIQUE NOT NULL,
                timestamp INTEGER NOT NULL,
                previous_block TEXT,
                nonce INTEGER,
                difficulty INTEGER DEFAULT 5,
                tx_hashes TEXT,
                fees_collected INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks(block_index)')
        
        try:
            cursor.execute('ALTER TABLE blocks ADD COLUMN fees_collected INTEGER DEFAULT 0')
        except:
            pass
        
        cursor.execute("PRAGMA table_info(blocks)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'fees_collected' not in columns:
            try:
                cursor.execute('ALTER TABLE blocks ADD COLUMN fees_collected INTEGER DEFAULT 0')
            except:
                pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                timestamp INTEGER NOT NULL,
                vin TEXT NOT NULL,
                vout TEXT NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_hash ON transactions(hash)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS untransactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                timestamp INTEGER NOT NULL,
                vin TEXT NOT NULL,
                vout TEXT NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_untx_hash ON untransactions(hash)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                pubkey TEXT,
                is_active INTEGER DEFAULT 0,
                encrypted_key TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_address ON accounts(address)')
        
        cursor.execute("PRAGMA table_info(accounts)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'is_active' not in columns:
            cursor.execute('ALTER TABLE accounts ADD COLUMN is_active INTEGER DEFAULT 0')
        if 'encrypted_key' not in columns:
            cursor.execute('ALTER TABLE accounts ADD COLUMN encrypted_key TEXT')
        if 'password_hash' not in columns:
            cursor.execute('ALTER TABLE accounts ADD COLUMN password_hash TEXT')
        if 'salt' not in columns:
            cursor.execute('ALTER TABLE accounts ADD COLUMN salt TEXT')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                last_seen INTEGER DEFAULT 0,
                is_alive INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_node_address ON nodes(address)')
        
        try:
            cursor.execute('ALTER TABLE nodes ADD COLUMN last_seen INTEGER DEFAULT 0')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE nodes ADD COLUMN is_alive INTEGER DEFAULT 1')
        except:
            pass

        conn.commit()


class BlockChainDB:
    def __init__(self):
        self.conn = SQLiteDB.get_conn()

    def find_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM blocks ORDER BY block_index')
        rows = cursor.fetchall()
        return [self._row_to_block_dict(row) for row in rows]

    def last(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1')
        row = cursor.fetchone()
        return self._row_to_block_dict(row) if row else []

    def find(self, hash):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM blocks WHERE hash = ?', (hash,))
        row = cursor.fetchone()
        return self._row_to_block_dict(row) if row else {}

    def insert(self, block):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO blocks (hash, block_index, timestamp, previous_block, nonce, difficulty, tx_hashes, fees_collected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            block['hash'],
            block['index'],
            block['timestamp'],
            block.get('previous_block', ''),
            block.get('nouce', 0),
            block.get('difficulty', 5),
            json.dumps(block.get('tx', [])),
            block.get('fees_collected', 0)
        ))
        self.conn.commit()

    def clear(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM blocks')
        self.conn.commit()

    def write(self, blocks):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM blocks')
        for block in blocks:
            cursor.execute('''
                INSERT INTO blocks (hash, block_index, timestamp, previous_block, nonce, difficulty, tx_hashes, fees_collected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                block['hash'],
                block['index'],
                block['timestamp'],
                block.get('previous_block', ''),
                block.get('nouce', 0),
                block.get('difficulty', 5),
                json.dumps(block.get('tx', [])),
                block.get('fees_collected', 0)
            ))
        self.conn.commit()

    def _row_to_block_dict(self, row):
        if not row:
            return {}
        fees = 0
        try:
            fees = row['fees_collected'] if row['fees_collected'] else 0
        except (KeyError, IndexError):
            fees = 0
        return {
            'hash': row['hash'],
            'index': row['block_index'],
            'timestamp': row['timestamp'],
            'previous_block': row['previous_block'],
            'nouce': row['nonce'],
            'difficulty': row['difficulty'],
            'tx': json.loads(row['tx_hashes']) if row['tx_hashes'] else [],
            'fees_collected': fees
        }


class TransactionDB:
    def __init__(self):
        self.conn = SQLiteDB.get_conn()

    def find_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM transactions ORDER BY id')
        rows = cursor.fetchall()
        return [self._row_to_tx_dict(row) for row in rows]

    def find(self, hash):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE hash = ?', (hash,))
        row = cursor.fetchone()
        return self._row_to_tx_dict(row) if row else {}

    def insert(self, txs):
        cursor = self.conn.cursor()
        if not isinstance(txs, list):
            txs = [txs]
        for tx in txs:
            cursor.execute('''
                INSERT OR IGNORE INTO transactions (hash, timestamp, vin, vout)
                VALUES (?, ?, ?, ?)
            ''', (
                tx['hash'],
                tx.get('timestamp', 0),
                json.dumps(tx.get('vin', [])),
                json.dumps(tx.get('vout', []))
            ))
        self.conn.commit()

    def hash_insert(self, tx):
        cursor = self.conn.cursor()
        cursor.execute('SELECT hash FROM transactions WHERE hash = ?', (tx['hash'],))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO transactions (hash, timestamp, vin, vout)
                VALUES (?, ?, ?, ?)
            ''', (
                tx['hash'],
                tx.get('timestamp', 0),
                json.dumps(tx.get('vin', [])),
                json.dumps(tx.get('vout', []))
            ))
            self.conn.commit()

    def write(self, txs):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM transactions')
        for tx in txs:
            cursor.execute('''
                INSERT INTO transactions (hash, timestamp, vin, vout)
                VALUES (?, ?, ?, ?)
            ''', (
                tx['hash'],
                tx.get('timestamp', 0),
                json.dumps(tx.get('vin', [])),
                json.dumps(tx.get('vout', []))
            ))
        self.conn.commit()

    def _row_to_tx_dict(self, row):
        if not row:
            return {}
        return {
            'hash': row['hash'],
            'timestamp': row['timestamp'],
            'vin': json.loads(row['vin']) if row['vin'] else [],
            'vout': json.loads(row['vout']) if row['vout'] else []
        }


class UnTransactionDB:
    def __init__(self):
        self.conn = SQLiteDB.get_conn()

    def find_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM untransactions ORDER BY id')
        rows = cursor.fetchall()
        return [self._row_to_tx_dict(row) for row in rows]

    def find(self, hash):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM untransactions WHERE hash = ?', (hash,))
        row = cursor.fetchone()
        return self._row_to_tx_dict(row) if row else {}

    def insert(self, txs):
        cursor = self.conn.cursor()
        if not isinstance(txs, list):
            txs = [txs]
        for tx in txs:
            cursor.execute('''
                INSERT OR IGNORE INTO untransactions (hash, timestamp, vin, vout)
                VALUES (?, ?, ?, ?)
            ''', (
                tx['hash'],
                tx.get('timestamp', 0),
                json.dumps(tx.get('vin', [])),
                json.dumps(tx.get('vout', []))
            ))
        self.conn.commit()

    def hash_insert(self, tx):
        cursor = self.conn.cursor()
        cursor.execute('SELECT hash FROM untransactions WHERE hash = ?', (tx['hash'],))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO untransactions (hash, timestamp, vin, vout)
                VALUES (?, ?, ?, ?)
            ''', (
                tx['hash'],
                tx.get('timestamp', 0),
                json.dumps(tx.get('vin', [])),
                json.dumps(tx.get('vout', []))
            ))
            self.conn.commit()

    def clear(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM untransactions')
        self.conn.commit()

    def write(self, txs):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM untransactions')
        for tx in txs:
            cursor.execute('''
                INSERT INTO untransactions (hash, timestamp, vin, vout)
                VALUES (?, ?, ?, ?)
            ''', (
                tx['hash'],
                tx.get('timestamp', 0),
                json.dumps(tx.get('vin', [])),
                json.dumps(tx.get('vout', []))
            ))
        self.conn.commit()

    def all_hashes(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT hash FROM untransactions')
        return [row['hash'] for row in cursor.fetchall()]

    def _row_to_tx_dict(self, row):
        if not row:
            return {}
        return {
            'hash': row['hash'],
            'timestamp': row['timestamp'],
            'vin': json.loads(row['vin']) if row['vin'] else [],
            'vout': json.loads(row['vout']) if row['vout'] else []
        }


class AccountDB:
    def __init__(self):
        self.conn = SQLiteDB.get_conn()

    def find_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY id')
        rows = cursor.fetchall()
        return [{'id': row['id'], 'address': row['address'], 'pubkey': row['pubkey'], 
                 'is_active': row['is_active'], 
                 'encrypted_key': row['encrypted_key'] if 'encrypted_key' in row.keys() else None,
                 'password_hash': row['password_hash'] if 'password_hash' in row.keys() else None,
                 'salt': row['salt'] if 'salt' in row.keys() else None} for row in rows]

    def find_one(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE is_active = 1 LIMIT 1')
        row = cursor.fetchone()
        if row:
            return {'id': row['id'], 'address': row['address'], 'pubkey': row['pubkey'], 
                    'is_active': row['is_active'], 
                    'encrypted_key': row['encrypted_key'] if 'encrypted_key' in row.keys() else None,
                    'password_hash': row['password_hash'] if 'password_hash' in row.keys() else None,
                    'salt': row['salt'] if 'salt' in row.keys() else None}
        cursor.execute('SELECT * FROM accounts ORDER BY id LIMIT 1')
        row = cursor.fetchone()
        if row:
            return {'id': row['id'], 'address': row['address'], 'pubkey': row['pubkey'], 
                    'is_active': row['is_active'], 
                    'encrypted_key': row['encrypted_key'] if 'encrypted_key' in row.keys() else None,
                    'password_hash': row['password_hash'] if 'password_hash' in row.keys() else None,
                    'salt': row['salt'] if 'salt' in row.keys() else None}
        return None

    def find_by_index(self, index):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY id LIMIT 1 OFFSET ?', (index - 1,))
        row = cursor.fetchone()
        if row:
            return {'id': row['id'], 'address': row['address'], 'pubkey': row['pubkey'], 
                    'is_active': row['is_active'], 
                    'encrypted_key': row['encrypted_key'] if 'encrypted_key' in row.keys() else None,
                    'password_hash': row['password_hash'] if 'password_hash' in row.keys() else None,
                    'salt': row['salt'] if 'salt' in row.keys() else None}
        return None

    def find_by_address(self, address):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE address = ?', (address,))
        row = cursor.fetchone()
        if row:
            return {'id': row['id'], 'address': row['address'], 'pubkey': row['pubkey'], 
                    'is_active': row['is_active'], 
                    'encrypted_key': row['encrypted_key'] if 'encrypted_key' in row.keys() else None,
                    'password_hash': row['password_hash'] if 'password_hash' in row.keys() else None,
                    'salt': row['salt'] if 'salt' in row.keys() else None}
        return None

    def set_active(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE accounts SET is_active = 0')
        cursor.execute('UPDATE accounts SET is_active = 1 WHERE id = ?', (account_id,))
        self.conn.commit()

    def clear_active(self):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE accounts SET is_active = 0')
        self.conn.commit()

    def update_encrypted_key(self, account_id, encrypted_key):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE accounts SET encrypted_key = ? WHERE id = ?', (encrypted_key, account_id))
        self.conn.commit()

    def insert(self, account):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM accounts')
        count = cursor.fetchone()[0]
        is_active = 1 if count == 0 else 0
        cursor.execute('''
            INSERT OR IGNORE INTO accounts (address, pubkey, is_active, encrypted_key)
            VALUES (?, ?, ?, ?)
        ''', (
            account['address'],
            account.get('pubkey', ''),
            is_active,
            account.get('encrypted_key', '')
        ))
        self.conn.commit()

    def clear(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM accounts')
        self.conn.commit()

    def write(self, accounts):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM accounts')
        for acc in accounts:
            cursor.execute('''
                INSERT INTO accounts (address, pubkey, is_active, encrypted_key)
                VALUES (?, ?, ?, ?)
            ''', (
                acc['address'],
                acc.get('pubkey', ''),
                acc.get('is_active', 0),
                acc.get('encrypted_key', '')
            ))
        self.conn.commit()


class NodeDB:
    def __init__(self):
        self.conn = SQLiteDB.get_conn()

    def find_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM nodes ORDER BY id')
        rows = cursor.fetchall()
        return [row['address'] for row in rows]

    def find_all_with_health(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM nodes ORDER BY id')
        rows = cursor.fetchall()
        return [{
            'address': row['address'],
            'last_seen': row['last_seen'] or 0,
            'is_alive': bool(row['is_alive']) if row['is_alive'] else False
        } for row in rows]

    def find_alive(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT address FROM nodes WHERE is_alive = 1 ORDER BY id')
        rows = cursor.fetchall()
        return [row['address'] for row in rows]

    def insert(self, node):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO nodes (address)
            VALUES (?)
        ''', (node,))
        self.conn.commit()

    def insert_with_health(self, address):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO nodes (address, last_seen, is_alive)
            VALUES (?, ?, ?)
        ''', (address, int(time.time()), 1))
        self.conn.commit()

    def update_last_seen(self, address):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE nodes SET last_seen = ?, is_alive = 1 WHERE address = ?
        ''', (int(time.time()), address))
        self.conn.commit()

    def set_alive(self, address, alive=True):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE nodes SET is_alive = ? WHERE address = ?
        ''', (1 if alive else 0, address))
        self.conn.commit()

    def get_node_status(self, address):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM nodes WHERE address = ?', (address,))
        row = cursor.fetchone()
        if row:
            return {
                'address': row['address'],
                'last_seen': row['last_seen'] or 0,
                'is_alive': bool(row['is_alive']) if row['is_alive'] else False
            }
        return None

    def get_all_node_status(self):
        return self.find_all_with_health()

    def remove(self, address):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM nodes WHERE address = ?', (address,))
        self.conn.commit()

    def clear(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM nodes')
        self.conn.commit()

    def write(self, nodes):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM nodes')
        for node in nodes:
            if isinstance(node, dict):
                cursor.execute('''
                    INSERT INTO nodes (address, last_seen, is_alive)
                    VALUES (?, ?, ?)
                ''', (node['address'], node.get('last_seen', 0), 1 if node.get('is_alive', True) else 0))
            else:
                cursor.execute('''
                    INSERT INTO nodes (address)
                    VALUES (?)
                ''', (node,))
        self.conn.commit()
