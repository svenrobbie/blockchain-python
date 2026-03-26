# coding:utf-8
import sqlite3
import json
import os

DATABASE_PATH = 'data/blockchain.db'


class SQLiteDB:
    _connection = None

    @classmethod
    def get_conn(cls):
        if cls._connection is None:
            os.makedirs('data', exist_ok=True)
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
                tx_hashes TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks(block_index)')

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
                pubkey TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_address ON accounts(address)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_node_address ON nodes(address)')

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
            INSERT OR IGNORE INTO blocks (hash, block_index, timestamp, previous_block, nonce, difficulty, tx_hashes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            block['hash'],
            block['index'],
            block['timestamp'],
            block.get('previous_block', ''),
            block.get('nouce', 0),
            block.get('difficulty', 5),
            json.dumps(block.get('tx', []))
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
                INSERT INTO blocks (hash, block_index, timestamp, previous_block, nonce, difficulty, tx_hashes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                block['hash'],
                block['index'],
                block['timestamp'],
                block.get('previous_block', ''),
                block.get('nouce', 0),
                block.get('difficulty', 5),
                json.dumps(block.get('tx', []))
            ))
        self.conn.commit()

    def _row_to_block_dict(self, row):
        if not row:
            return {}
        return {
            'hash': row['hash'],
            'index': row['block_index'],
            'timestamp': row['timestamp'],
            'previous_block': row['previous_block'],
            'nouce': row['nonce'],
            'difficulty': row['difficulty'],
            'tx': json.loads(row['tx_hashes']) if row['tx_hashes'] else []
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
        return [{'address': row['address'], 'pubkey': row['pubkey']} for row in rows]

    def find_one(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY id LIMIT 1')
        row = cursor.fetchone()
        if row:
            return {'address': row['address'], 'pubkey': row['pubkey']}
        return None

    def insert(self, account):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO accounts (address, pubkey)
            VALUES (?, ?)
        ''', (
            account['address'],
            account.get('pubkey', '')
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
                INSERT INTO accounts (address, pubkey)
                VALUES (?, ?)
            ''', (
                acc['address'],
                acc.get('pubkey', '')
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

    def insert(self, node):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO nodes (address)
            VALUES (?)
        ''', (node,))
        self.conn.commit()

    def clear(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM nodes')
        self.conn.commit()

    def write(self, nodes):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM nodes')
        for node in nodes:
            cursor.execute('''
                INSERT INTO nodes (address)
                VALUES (?)
            ''', (node,))
        self.conn.commit()
