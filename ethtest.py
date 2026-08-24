from os import environ
import sys

from web3 import Web3

node_url = environ.get("ETH_URL") or "http://127.0.0.1:8545"

try:
    print(f"Connecting to Ethereum node at {node_url}…")
    if node_url.startswith("http://") or node_url.startswith("https://"):
        web3 = Web3(Web3.HTTPProvider(node_url))
    elif node_url.startswith("ws://") or node_url.startswith("wss://"):
        web3 = Web3(Web3.WebsocketProvider(node_url))
    else:
        web3 = Web3(Web3.IPCProvider(node_url))

    best_block = web3.eth.block_number
    sync_status = web3.eth.syncing
    print(f"Connected successfully. Current best block: {best_block}, syncing: {sync_status}")
except Exception as e:
    print(f"Failed to connect to Ethereum node at {node_url}: {e}")
    sys.exit(1)
