#! /usr/bin/env python3
# coding:utf-8
"""
Blockchain Python - Main Entry Point

Usage:
    python blockchain.py [command] [args]

Commands:
    wallet new <password>     Create new wallet
    wallet list               List all accounts
    wallet login <index>      Switch to account
    wallet balance            Show balance
    wallet address            Show address
    
    send <to> <amount> <password>  Send coins
    
    mine start                Start mining
    mine stop                 Stop mining
    
    node connect <host:port>  Add peer node
    node list                 List nodes
    node discover             Discover nodes via mDNS
    
    chain status              Chain statistics
    chain block <index>       View block details
    chain tx <hash>           View transaction
    chain verify              Verify chain integrity
    
    start                     Start web UI + node
    console                   Interactive mode
    status                    Quick status
    pending                   List pending transactions
    --help                    Show this help
"""

import argparse
import sys

from lib.common import colored

from cli.console import Console
from cli.commands import register_commands


def create_parser():
    parser = argparse.ArgumentParser(
        description='Blockchain Python - A Python blockchain implementation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python blockchain.py wallet new mypassword
  python blockchain.py wallet list
  python blockchain.py wallet login 1
  python blockchain.py send 1ABC...XYZ 100 mypassword
  python blockchain.py mine start
  python blockchain.py chain status
  python blockchain.py start
  python blockchain.py console
        """
    )
    
    parser.add_argument('--version', action='version', version='Blockchain Python v1.0')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    start_parser = subparsers.add_parser('start', help='Start web UI and node server')
    start_parser.add_argument('--port', type=int, default=5001, help='Web UI port (default: 5001)')
    start_parser.add_argument('--node-port', type=int, default=3009, help='Node RPC port (default: 3009)')
    start_parser.set_defaults(func=cmd_start)
    
    console_parser = subparsers.add_parser('console', help='Start interactive console mode')
    console_parser.set_defaults(func=cmd_console)
    
    register_commands(subparsers)
    
    return parser


def cmd_start(args):
    import web.main
    import uvicorn
    import node
    
    print(colored("\n=== Starting Blockchain Python ===", "cyan", bold=True))
    print(colored("Initializing node...", "white"))
    
    node.init_node()
    print(colored("  - RPC server initialized", "green"))
    
    print(colored("\nStarting web UI on port {}...".format(args.port), "white"))
    print(colored("Press Ctrl+C to stop\n", "dim"))
    
    try:
        uvicorn.run(web.main.app, host="0.0.0.0", port=args.port, log_level="warning")
    except KeyboardInterrupt:
        print(colored("\n\nShutting down...", "yellow"))


def cmd_console(args):
    console = Console()
    console.run()


def main():
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        print(colored("Blockchain Python v1.0\n", "cyan", bold=True))
        print("Starting interactive console...\n")
        console = Console()
        console.run()
        return
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
