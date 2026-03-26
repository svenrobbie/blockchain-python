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
    from blockchain import node
    
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


def show_menu():
    banner = """
 +------------------------------------------------------------+
 |                                                            |
 |   BBBBB    L      OOOOO   CCCCC  KKKK   KKKK  CCCCCC  HHHH  |
 |   BB  BB   L      OO  OO  CC      KK K  KK KK  CC       HHHH |
 |   BBBBBB   L      OO  OO  CC      KKKK   KKKK  CC       HHHH |
 |   BB  BB   L      OO  OO  CC      KK KK  KK KK  CC       HHHH |
 |   BBBBB    LLLLL   OOOO   CCCCC  KK  K  KK  K  CCCCC  HHHH |
 |                                                            |
 |   P     Y     TTTTT  H     H  OOO   N    N                 |
 |   P     Y       T    H     H  O  O  NN   N                 |
 |   PPPPPPY       T    HHHHHHH  O  O  N N  N                 |
 |   P     Y       T    H     H  OOOO  N  N N                 |
 |                                                            |
 +------------------------------------------------------------+
"""
    print(colored(banner, "cyan"))
    print(colored("  Welcome to Blockchain Python v1.0!\n", "yellow", bold=True))
    
    print("  Choose an option:\n")
    print(f"  {colored('[1]', 'cyan')}  {colored('Web UI', 'green')}     - Start the web interface (recommended)")
    print(f"  {colored('[2]', 'cyan')}  {colored('Console', 'green')}    - Start interactive CLI")
    print(f"  {colored('[3]', 'cyan')}  {colored('Help', 'green')}       - Show all commands")
    print(f"  {colored('[Q]', 'red')}   {colored('Quit', 'red')}       - Exit\n")
    
    while True:
        choice = input(colored("  > ", "yellow")).strip().lower()
        
        if choice == '1':
            print()
            args = argparse.Namespace(port=5001, node_port=3009)
            cmd_start(args)
            break
        elif choice == '2':
            print()
            cmd_console(None)
            break
        elif choice == '3':
            parser = create_parser()
            parser.print_help()
            print()
        elif choice in ('q', 'quit', 'exit'):
            print(colored("\nGoodbye! Keep on blockchainin'!\n", "yellow"))
            break
        else:
            print(colored("  Invalid choice. Please enter 1, 2, 3, or Q.\n", "red"))


def main():
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        show_menu()
        return
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
