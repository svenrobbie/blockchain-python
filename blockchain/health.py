# coding:utf-8
import threading
import time
import socket
from lib.common import cprint

PING_INTERVAL = 60
PING_TIMEOUT = 10
MAX_FAILURES = 5


class NodeHealthMonitor:
    def __init__(self):
        self.running = False
        self.thread = None
        self.failed_attempts = {}

    def start(self):
        if self.running:
            cprint("WARN", "Health monitor already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        cprint("INFO", f"Node health monitor started (ping every {PING_INTERVAL}s)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        cprint("INFO", "Node health monitor stopped")

    def _ping_loop(self):
        while self.running:
            time.sleep(PING_INTERVAL)
            
            if not self.running:
                break

            try:
                self._ping_all_nodes()
            except Exception as e:
                cprint("ERROR", f"Health check error: {e}")

    def _ping_all_nodes(self):
        from blockchain.database import NodeDB
        ndb = NodeDB()
        nodes = ndb.find_all()

        for node in nodes:
            address = node if isinstance(node, str) else node.get('address', '')
            
            if not address:
                continue

            try:
                success = self._ping_node(address)
                
                if success:
                    if address in self.failed_attempts:
                        del self.failed_attempts[address]
                    ndb.update_last_seen(address)
                    ndb.set_alive(address, True)
                else:
                    self._handle_failure(address)
                    
            except Exception as e:
                self._handle_failure(address)

    def _ping_node(self, address):
        try:
            from xmlrpc.client import ServerProxy
            
            if not address.startswith('http'):
                address = 'http://' + address
            
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(PING_TIMEOUT)
            try:
                client = ServerProxy(address, allow_none=True)
                result = client.ping()
                return result is True
            finally:
                socket.setdefaulttimeout(old_timeout)
        except socket.timeout:
            cprint("WARN", f"Node {address} ping timeout")
            return False
        except ConnectionRefusedError:
            cprint("WARN", f"Node {address} connection refused")
            return False
        except Exception as e:
            cprint("WARN", f"Node {address} ping failed: {e}")
            return False

    def _handle_failure(self, address):
        if address not in self.failed_attempts:
            self.failed_attempts[address] = 0
        
        self.failed_attempts[address] += 1
        
        failures = self.failed_attempts[address]
        
        if failures >= MAX_FAILURES:
            cprint("ERROR", f"Node {address} marked as dead after {failures} failures")
            self._remove_node(address)
        else:
            cprint("WARN", f"Node {address} failed ping ({failures}/{MAX_FAILURES})")
            self._mark_node_dead(address)

    def _mark_node_dead(self, address):
        from blockchain.database import NodeDB
        ndb = NodeDB()
        ndb.set_alive(address, False)

    def _remove_node(self, address):
        from blockchain.database import NodeDB
        ndb = NodeDB()
        ndb.remove(address)
        cprint("INFO", f"Removed dead node: {address}")
        
        if address in self.failed_attempts:
            del self.failed_attempts[address]

    def ping_node_now(self, address):
        success = self._ping_node(address)
        if success:
            self.failed_attempts.pop(address, None)
        return success

    def get_node_status(self, address):
        from blockchain.database import NodeDB
        ndb = NodeDB()
        return ndb.get_node_status(address)

    def get_all_status(self):
        from blockchain.database import NodeDB
        ndb = NodeDB()
        return ndb.get_all_node_status()


def ping_node(address, timeout=PING_TIMEOUT):
    monitor = NodeHealthMonitor()
    return monitor.ping_node_now(address)


if __name__ == '__main__':
    print("Testing health monitor...")
    monitor = NodeHealthMonitor()
    
    print("Starting health monitor...")
    monitor.start()
    
    print(f"Ping interval: {PING_INTERVAL}s")
    print(f"Max failures before removal: {MAX_FAILURES}")
    print(f"Timeout: {PING_TIMEOUT}s")
    
    time.sleep(5)
    
    print("Stopping health monitor...")
    monitor.stop()
