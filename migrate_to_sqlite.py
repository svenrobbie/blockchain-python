# coding:utf-8
import os
import shutil
from database import BlockChainDB as OldBlockDB, TransactionDB as OldTxDB
from database import UnTransactionDB as OldUnTxDB, AccountDB as OldAccountDB
from database import NodeDB as OldNodeDB
from database_sqlite import SQLiteDB
from database_sqlite import BlockChainDB as NewBlockDB, TransactionDB as NewTxDB
from database_sqlite import UnTransactionDB as NewUnTxDB, AccountDB as NewAccountDB
from database_sqlite import NodeDB as NewNodeDB


def backup_old_files():
    print("Creating backup of old database files...")
    backup_dir = 'data/backup_json'
    os.makedirs(backup_dir, exist_ok=True)
    
    files = ['blockchain', 'tx', 'untx', 'account', 'node']
    for f in files:
        src = f'data/{f}'
        if os.path.exists(src):
            shutil.copy2(src, f'{backup_dir}/{f}')
            print(f"  Backed up: {f}")
    
    print(f"Backup saved to: {backup_dir}/\n")


def migrate_blockchain():
    print("Migrating blockchain...")
    old_db = OldBlockDB()
    new_db = NewBlockDB()
    
    blocks = old_db.find_all()
    new_db.write(blocks)
    
    print(f"  Migrated {len(blocks)} blocks\n")
    return len(blocks)


def migrate_transactions():
    print("Migrating transactions...")
    old_db = OldTxDB()
    new_db = NewTxDB()
    
    txs = old_db.find_all()
    if txs:
        new_db.write(txs)
    
    print(f"  Migrated {len(txs)} transactions\n")
    return len(txs)


def migrate_untransactions():
    print("Migrating unconfirmed transactions...")
    old_db = OldUnTxDB()
    new_db = NewUnTxDB()
    
    txs = old_db.find_all()
    if txs:
        new_db.write(txs)
    
    print(f"  Migrated {len(txs)} unconfirmed transactions\n")
    return len(txs)


def migrate_accounts():
    print("Migrating accounts...")
    old_db = OldAccountDB()
    new_db = NewAccountDB()
    
    accounts = old_db.find_all()
    if accounts:
        new_db.write(accounts)
    
    print(f"  Migrated {len(accounts)} accounts\n")
    return len(accounts)


def migrate_nodes():
    print("Migrating nodes...")
    old_db = OldNodeDB()
    new_db = NewNodeDB()
    
    nodes = old_db.find_all()
    if nodes:
        new_db.write(nodes)
    
    print(f"  Migrated {len(nodes)} nodes\n")
    return len(nodes)


def verify_migration():
    print("Verifying migration...")
    
    old_blocks = OldBlockDB().find_all()
    new_blocks = NewBlockDB().find_all()
    
    old_txs = OldTxDB().find_all()
    new_txs = NewTxDB().find_all()
    
    print(f"  Blocks: {len(old_blocks)} -> {len(new_blocks)} {'OK' if len(old_blocks) == len(new_blocks) else 'MISMATCH'}")
    print(f"  Transactions: {len(old_txs)} -> {len(new_txs)} {'OK' if len(old_txs) == len(new_txs) else 'MISMATCH'}")
    
    if old_blocks and new_blocks:
        if old_blocks[-1]['hash'] == new_blocks[-1]['hash']:
            print(f"  Latest block hash matches: OK")
        else:
            print(f"  Latest block hash: MISMATCH!")
    
    print()


def migrate():
    print("=" * 50)
    print("SQLite Migration Script")
    print("=" * 50 + "\n")
    
    print("Step 1: Initialize SQLite database...")
    SQLiteDB.init_db()
    print("  Done!\n")
    
    print("Step 2: Backup old JSON files...")
    backup_old_files()
    
    print("Step 3: Migrating data...\n")
    migrate_blockchain()
    migrate_transactions()
    migrate_untransactions()
    migrate_accounts()
    migrate_nodes()
    
    print("Step 4: Verifying migration...")
    verify_migration()
    
    print("=" * 50)
    print("Migration complete!")
    print("=" * 50)
    print("\nOld JSON files preserved in: data/backup_json/")
    print("New SQLite database at: data/blockchain.db")
    print("\nTo use new database, update imports in your code.")
    print("To rollback, restore from data/backup_json/")


if __name__ == '__main__':
    migrate()
