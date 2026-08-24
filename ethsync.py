# Indexer for Ethereum to get transaction list by ETH address
# https://github.com/Adamant-im/ETH-transactions-storage

# Contributors:
# v2.5.0
# 2025-2026 ADAMANT developer community (devs@adamant.im)
# 2022-2024 ADAMANT Foundation (devs@adamant.im), @twhitehead00, Tyvan Cheng (tyvancheng@gmail.com)
# 2021-2022 ADAMANT Foundation (devs@adamant.im), Francesco Bonanno (mibofra@parrotsec.org),
# Guénolé de Cadoudal (guenoledc@yahoo.fr), Drew Wells (drew.wells00@gmail.com)
# 2020-2021 ADAMANT Foundation (devs@adamant.im): Aleksei Lebedev
# 2017-2020 ADAMANT TECH LABS LP (pr@adamant.im): Artem Brunov, Aleksei Lebedev

import json
import logging
from os import environ
from pathlib import Path
import sys
import time

import psycopg2
from web3 import Web3
from web3.middleware import geth_poa_middleware


def get_version():
    """Reads application version from package.json."""
    try:
        package_json_path = Path(__file__).resolve().parent / "package.json"
        with open(package_json_path, "r", encoding="utf-8") as f:
            return json.load(f).get("version", "undefined")
    except Exception:
        return "undefined"


__version__ = get_version()

# Get environment variables or set defaults
dbname = environ.get("DB_NAME")
start_block = environ.get("START_BLOCK") or "1"
confirmation_blocks = environ.get("CONFIRMATIONS_BLOCK") or "0"
node_url = environ.get("ETH_URL")
polling_period = environ.get("PERIOD") or "20"
log_file = environ.get("LOG_FILE")

if dbname is None:
    print("Set PostgreSQL database in environment variable DB_NAME")
    sys.exit(2)

if node_url is None:
    print("Set Ethereum node URL in environment variable ETH_URL")
    sys.exit(2)

# Connect to Ethereum node
if node_url.startswith("http://") or node_url.startswith("https://"):
    web3 = Web3(Web3.HTTPProvider(node_url)) # "http://publicnode:8545"
elif node_url.startswith("ws://") or node_url.startswith("wss://"):
    web3 = Web3(Web3.WebsocketProvider(node_url)) # "ws://publicnode:8546"
else:
    web3 = Web3(Web3.IPCProvider(node_url)) # "/home/geth/.ethereum/geth.ipc"

web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Configure logger
logger = logging.getLogger("eth-sync")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

if log_file is None:
    handler = logging.StreamHandler()
else:
    handler = logging.FileHandler(log_file)

handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info(f"Starting Ethereum Transactions Storage v{__version__}…")

# Connect to database and clean up the last block on startup
try:
    logger.info(f"Connecting to '{dbname}' database…")
    conn = psycopg2.connect(database=dbname)
    conn.autocommit = True
    logger.info("Connected to the database")

    # Delete last block on startup in case it was partially indexed
    cur = conn.cursor()
    cur.execute("DELETE FROM public.ethtxs WHERE block = (SELECT MAX(block) FROM public.ethtxs);")
    cur.close()
    conn.close()
except Exception as e:
    logger.error(f"Unable to connect to database or clean up initial block: {e}")
    sys.exit(1)

# Wait for the Ethereum node to be in sync before indexing
while bool(web3.eth.syncing):
    logger.info("Waiting for Ethereum node to finish synchronizing… (retrying in 5 minutes)")
    time.sleep(300)

logger.info("Ethereum node is synchronized.")


def insert_txs_from_block(block, cursor):
    """Parses and inserts native ETH and ERC-20 transfer transactions from a block."""
    block_id = block["number"]
    tx_time = block["timestamp"]

    for tx in block.transactions:
        tx_receipt = web3.eth.get_transaction_receipt(tx["hash"])
        tx_hash = tx["hash"].hex()
        value = tx["value"]
        input_data = tx["input"]
        input_hex = input_data.hex() if hasattr(input_data, "hex") else str(input_data)

        # Skip non-transfer transactions: zero value and not an ERC-20 transfer (0xa9059cbb)
        if value == 0 and not input_hex.startswith("0xa9059cbb"):
            continue

        tx_from = tx["from"]
        tx_to = tx["to"]
        gas_price = tx["gasPrice"]
        gas = tx_receipt["gasUsed"]
        contract_to = ""
        contract_value = ""

        # Parse ERC-20 transfer method (0xa9059cbb + 32-byte recipient + 32-byte amount)
        if input_hex.startswith("0xa9059cbb"):
            contract_to = input_hex[10:-64]
            contract_value = input_hex[74:]

        # Filter out malformed contract transfer inputs
        if len(contract_to) > 128:
            logger.info(f"Skipping tx {tx_hash}: unexpected contract_to length ({len(contract_to)})")
            contract_to = ""
            contract_value = ""

        cursor.execute(
            """
            INSERT INTO public.ethtxs(
                time, txfrom, txto, value, gas, gasprice, block, txhash, contract_to, contract_value
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tx_time,
                tx_from,
                tx_to,
                value,
                gas,
                gas_price,
                block_id,
                tx_hash,
                contract_to,
                contract_value,
            ),
        )


# Main synchronization loop
while True:
    try:
        conn = psycopg2.connect(database=dbname)
        conn.autocommit = False
    except Exception as e:
        logger.error(f"Unable to connect to database: {e}")
        time.sleep(int(polling_period))
        continue

    cur = conn.cursor()

    try:
        cur.execute("SELECT MAX(block) FROM public.ethtxs;")
        max_block_in_db = cur.fetchone()[0]

        # On first start with an empty database, index from START_BLOCK
        if max_block_in_db is None:
            max_block_in_db = int(start_block)

        end_block = int(web3.eth.block_number) - int(confirmation_blocks)

        logger.info(f"Current best block in index: {max_block_in_db}; in Ethereum chain: {end_block}")

        for block_height in range(max_block_in_db + 1, end_block):
            block = web3.eth.get_block(block_height, True)
            if len(block.transactions) > 0:
                insert_txs_from_block(block, cur)
                conn.commit()
                logger.info(f"Block {block_height} with {len(block.transactions)} transactions processed")
            else:
                logger.info(f"Block {block_height} contains no transactions")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during synchronization pass: {e}")
    finally:
        cur.close()
        conn.close()

    time.sleep(int(polling_period))
