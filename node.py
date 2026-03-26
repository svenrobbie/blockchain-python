# coding:utf-8
import multiprocessing
import time
import rpc
from database_sqlite import NodeDB, TransactionDB, BlockChainDB
from lib.common import cprint

discovery_instance = None
health_instance = None


def start_node(hostport='0.0.0.0:3009'):
    global discovery_instance, health_instance
    
    init_node()
    cprint('INFO', 'Node initialize success.')
    
    try:
        if hostport.find('.') != -1:
            host, port = hostport.split(':')
        else:
            host = '0.0.0.0'
            port = hostport
    except Exception:
        cprint('ERROR', 'params must be {port} or {host}:{port}, ps: 3009 or 0.0.0.0:3009')
        return

    try:
        port = int(port)
    except ValueError:
        cprint('ERROR', f'Invalid port: {port}')
        return

    p = multiprocessing.Process(target=rpc.start_server, args=(host, port))
    p.start()
    cprint('INFO', 'Node start success. Listen at %s.' % (hostport,))

    try:
        from node_discovery import NodeDiscovery
        discovery_instance = NodeDiscovery(port=port)
        discovery_instance.start()
    except Exception as e:
        cprint('WARN', f'Failed to start discovery: {e}')

    try:
        from node_health import NodeHealthMonitor
        health_instance = NodeHealthMonitor()
        health_instance.start()
    except Exception as e:
        cprint('WARN', f'Failed to start health monitor: {e}')


def stop_node():
    global discovery_instance, health_instance
    
    if discovery_instance:
        discovery_instance.stop()
        discovery_instance = None
    
    if health_instance:
        health_instance.stop()
        health_instance = None
    
    cprint('INFO', 'Node services stopped')


def init_node():
    """
    Download blockchain from node compare with local database and select the longest blockchain.
    Only syncs with alive nodes.
    """
    ndb = NodeDB()
    alive_nodes = ndb.find_alive()
    
    all_node_blockchains = []
    all_node_txs = []
    
    for node in alive_nodes:
        try:
            bc = rpc.RpcClient(node).get_blockchain()
            txs = rpc.RpcClient(node).get_transactions()
            if bc:
                all_node_blockchains.append(bc)
            if txs:
                all_node_txs.append(txs)
        except Exception as e:
            cprint('WARN', f'Failed to sync from {node}: {e}')
            ndb.set_alive(node, False)

    bcdb = BlockChainDB()
    txdb = TransactionDB()
    blockchain = bcdb.find_all()
    transactions = txdb.find_all()
    
    for bc in all_node_blockchains:
        if len(bc) > len(blockchain):
            bcdb.clear()
            bcdb.write(bc)
            blockchain = bc
    
    for txs in all_node_txs:
        if len(txs) > len(transactions):
            txdb.clear()
            txdb.write(txs)
            transactions = txs


def get_nodes():
    return NodeDB().find_all()


def get_alive_nodes():
    return NodeDB().find_alive()


def get_nodes_status():
    return NodeDB().find_all_with_health()


def add_node(address):
    ndb = NodeDB()
    if address.find('http') != 0:
        address = 'http://' + address
    ndb.insert_with_health(address)
    cprint('INFO', f'Added node: {address}')
    return address


def check_node(address):
    try:
        from node_health import ping_node
        return ping_node(address)
    except Exception as e:
        cprint('ERROR', f'Node check failed: {e}')
        return False


def rm_dup(nodes):
    return sorted(set(nodes))


def get_node_status(address=None):
    if address:
        return NodeDB().get_node_status(address)
    return NodeDB().get_all_node_status()


if __name__ == '__main__':
    start_node('0.0.0.0:3009')
