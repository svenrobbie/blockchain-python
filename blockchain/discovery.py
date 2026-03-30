# coding:utf-8
import socket
import threading
import time
from lib.common import cprint
from blockchain.config import DISCOVERY_PORT, VERSION, DISCOVERY_INTERVAL

try:
    from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    ServiceBrowser = None
    cprint("WARN", "python-zeroconf not installed. Run: pip install zeroconf")

SERVICE_TYPE = "_blockchain._tcp.local."
SERVICE_NAME = "Blockchain_Python"


class NodeDiscovery:
    def __init__(self, port=DISCOVERY_PORT, version=VERSION):
        self.port = port
        self.version = version
        self.running = False
        self.thread = None
        self.zeroconf = None
        self.service_info = None
        self.discovered_nodes = []
        self.browser = None
        self.listener = None

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def register_service(self):
        if not ZEROCONF_AVAILABLE:
            cprint("WARN", "mDNS registration skipped - zeroconf not installed")
            return False

        try:
            self.zeroconf = Zeroconf()
            self.service_info = ServiceInfo(
                SERVICE_TYPE,
                f"{SERVICE_NAME}_{self.port}.{SERVICE_TYPE}",
                addresses=[socket.inet_aton(self.get_local_ip())],
                port=self.port,
                properties={'version': self.version}
            )
            self.zeroconf.register_service(self.service_info)
            cprint("INFO", f"mDNS service registered: {SERVICE_NAME} on port {self.port}")
            return True
        except Exception as e:
            cprint("ERROR", f"Failed to register mDNS service: {e}")
            return False

    def unregister_service(self):
        if self.zeroconf and self.service_info:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                cprint("INFO", "mDNS service unregistered")
            except Exception as e:
                cprint("ERROR", f"Failed to unregister mDNS service: {e}")

    def start_discovery(self):
        if not ZEROCONF_AVAILABLE:
            cprint("WARN", "mDNS discovery skipped - zeroconf not installed")
            return []

        try:
            self.zeroconf = Zeroconf()
            self.discovered_nodes = []
            self.listener = NodeDiscoveryListener(self.discovered_nodes)
            self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self.listener)
            cprint("INFO", "mDNS discovery started")
            return self.discovered_nodes
        except Exception as e:
            cprint("ERROR", f"Failed to start mDNS discovery: {e}")
            return []

    def stop_discovery(self):
        if self.zeroconf:
            try:
                if self.browser:
                    self.browser.cancel()
                self.zeroconf.close()
                cprint("INFO", "mDNS discovery stopped")
            except Exception as e:
                cprint("ERROR", f"Error stopping mDNS discovery: {e}")

    def discover_nodes(self, timeout=5):
        if not ZEROCONF_AVAILABLE:
            return []

        try:
            discovered = []
            self.discovered_nodes = []
            self.zeroconf = Zeroconf()
            self.listener = NodeDiscoveryListener(self.discovered_nodes)
            self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self.listener)
            
            time.sleep(timeout)
            
            for info in self.discovered_nodes:
                addresses = info.addresses
                if addresses:
                    ip = socket.inet_ntoa(addresses[0])
                    port = info.port
                    address = f"http://{ip}:{port}"
                    discovered.append({
                        'address': address,
                        'version': info.properties.get(b'version', b'1.0').decode('utf-8')
                    })
            
            if self.zeroconf:
                self.zeroconf.close()
            
            return discovered
        except Exception as e:
            cprint("ERROR", f"Discovery failed: {e}")
            return []

    def start(self):
        if self.running:
            cprint("WARN", "Discovery already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.thread.start()
        cprint("INFO", "Node discovery started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.unregister_service()
        self.stop_discovery()
        cprint("INFO", "Node discovery stopped")

    def _discovery_loop(self):
        self.register_service()
        time.sleep(2)
        self.start_discovery()

        while self.running:
            time.sleep(DISCOVERY_INTERVAL)
            
            if not ZEROCONF_AVAILABLE:
                continue

            try:
                new_nodes = self.discover_nodes(timeout=3)
                for node in new_nodes:
                    self._add_discovered_node(node)
            except Exception as e:
                cprint("ERROR", f"Discovery loop error: {e}")

    def _add_discovered_node(self, node_info):
        from blockchain.database import NodeDB
        ndb = NodeDB()
        existing = ndb.find_all()
        addresses = [n['address'] if isinstance(n, dict) else n for n in existing]
        
        address = node_info['address']
        if address not in addresses:
            ndb.insert_with_health(address)
            cprint("INFO", f"Auto-discovered new node: {address}")


class NodeDiscoveryListener:
    def __init__(self, discovered_list):
        self.discovered_list = discovered_list

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            self.discovered_list.append(info)

    def remove_service(self, zc, type_, name):
        pass

    def update_service(self, zc, type_, name):
        pass


def auto_discover_nodes(timeout=5):
    discovery = NodeDiscovery()
    return discovery.discover_nodes(timeout=timeout)


if __name__ == '__main__':
    print("Testing mDNS discovery...")
    discovery = NodeDiscovery(port=3009)
    
    print("Registering service...")
    discovery.register_service()
    
    print(f"Local IP: {discovery.get_local_ip()}")
    
    print("Discovering nodes (5 seconds)...")
    nodes = discovery.discover_nodes(timeout=5)
    
    print(f"Found {len(nodes)} nodes:")
    for node in nodes:
        print(f"  - {node}")
    
    discovery.unregister_service()
