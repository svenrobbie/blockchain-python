# coding:utf-8
from xmlrpc.server import SimpleXMLRPCServer  
from xmlrpc.client import ServerProxy
from blockchain.database import BlockChainDB, UnTransactionDB, TransactionDB
from lib.common import cprint
server = None

PORT = 8301

class RpcServer():

    VERSION = "1.0"

    def __init__(self, server):
        self.server = server

    def ping(self):
        return True

    def get_version(self):
        return self.VERSION

    def get_blockchain(self):
        bcdb = BlockChainDB()
        return bcdb.find_all()

    def new_block(self,block):
        cprint('RPC', block)
        
        BlockChainDB().insert(block)
        UnTransactionDB().clear()
        cprint('INFO',"Receive new block.")
        return True

    def get_transactions(self):
        tdb = TransactionDB()
        return tdb.find_all()

    def new_untransaction(self,untx):
        cprint(__name__,untx)
        UnTransactionDB().insert(untx)
        cprint('INFO',"Receive new unchecked transaction.")
        return True

    def blocked_transactions(self,txs):
        TransactionDB().write(txs)
        cprint('INFO',"Receive new blocked transactions.")
        return True

    def add_node(self, address):
        from blockchain import node
        node.add_node(address)
        return True

class RpcClient():

    ALLOW_METHOD = ['get_transactions', 'get_blockchain', 'new_block', 'new_untransaction', 'blocked_transactions', 'ping', 'add_node', 'get_version']

    def __init__(self, node):
        self.node = node
        self.client = ServerProxy(node)
    
    def __getattr__(self, name):
        def noname(*args, **kw):
            if name in self.ALLOW_METHOD:
                return getattr(self.client, name)(*args, **kw)
        return noname

class BroadCast():

    def __getattr__(self, name):
        def noname(*args, **kw):
            cs = get_clients()
            rs = []
            for c in cs:
                try:
                    result = getattr(c, name)(*args, **kw)
                    rs.append(result)
                    cprint('INFO', 'Contact with node %s successful calling method %s .' % (c.node, name))
                except ConnectionRefusedError:
                    cprint('WARN', 'Contact with node %s failed when calling method %s , please check the node.' % (c.node, name))
                except Exception as e:
                    cprint('WARN', 'Error contacting node %s: %s' % (c.node, str(e)))
            return rs if rs else True
        return noname

def start_server(ip, port=8301):
    server = SimpleXMLRPCServer((ip, port))
    rpc = RpcServer(server)
    server.register_instance(rpc)
    server.serve_forever()

def get_clients():
    from blockchain import node
    clients = []
    nodes = node.get_nodes()

    for node in nodes:
        clients.append(RpcClient(node))
    return clients
