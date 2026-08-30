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

from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

from address_filter import (
    load_monitored_addresses,
    parse_boolean,
    transaction_matches_filter,
)
from database import connect_database, sanitize_database_error


PROJECT_DIRECTORY = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIRECTORY / ".env", override=False)


def get_version():
    """Reads application version from package.json."""
    try:
        package_json_path = PROJECT_DIRECTORY / "package.json"
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
log_file = environ.get("LOG_FILE") or None
address_filter_enabled_value = environ.get("ADDRESS_FILTER_ENABLED") or "false"
address_filter_file = Path(
    environ.get("ADDRESS_FILTER_FILE") or "filter/addresses.txt"
).expanduser()

if not address_filter_file.is_absolute():
    address_filter_file = PROJECT_DIRECTORY / address_filter_file

if dbname is None:
    print("Set PostgreSQL database in environment variable DB_NAME")
    sys.exit(2)

if node_url is None:
    print("Set Ethereum node URL in environment variable ETH_URL")
    sys.exit(2)

# Connect to Ethereum node
if node_url.startswith("http://") or node_url.startswith("https://"):
    web3 = Web3(Web3.HTTPProvider(node_url))  # "http://publicnode:8545"
elif node_url.startswith("ws://") or node_url.startswith("wss://"):
    web3 = Web3(Web3.WebsocketProvider(node_url))  # "ws://publicnode:8546"
else:
    web3 = Web3(Web3.IPCProvider(node_url))  # "/home/geth/.ethereum/geth.ipc"

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

try:
    address_filter_enabled = parse_boolean(
        address_filter_enabled_value, "ADDRESS_FILTER_ENABLED"
    )
    monitored_addresses = (
        load_monitored_addresses(address_filter_file)
        if address_filter_enabled
        else frozenset()
    )
except ValueError as e:
    logger.error(f"Unable to configure address filter: {e}")
    sys.exit(2)

if address_filter_enabled:
    logger.info(
        f"Address filter enabled with {len(monitored_addresses)} monitored addresses "
        f"from '{address_filter_file}'"
    )
else:
    logger.info("Address filter disabled")

# Connect to the database before initializing the checkpoint.
try:
    logger.info("Connecting to PostgreSQL database…")
    conn = connect_database(dbname)
    logger.info("Connected to the database")
except Exception as e:
    logger.error(
        f"Unable to connect to PostgreSQL database: {sanitize_database_error(e)}"
    )
    sys.exit(1)

# Clean up the last block on startup in case it was partially indexed.
cur = None
try:
    conn.autocommit = False
    # Delete last block on startup in case it was partially indexed
    cur = conn.cursor()
    cur.execute(
        """
        SELECT GREATEST(
            (SELECT MAX(block) FROM public.ethtxs),
            (SELECT last_block FROM public.sync_state WHERE singleton = TRUE)
        );
        """
    )
    last_processed_block = cur.fetchone()[0]
    if last_processed_block is not None:
        cur.execute("DELETE FROM public.ethtxs WHERE block = %s;", (last_processed_block,))
        cur.execute(
            """
            UPDATE public.sync_state
            SET last_block = %s
            WHERE singleton = TRUE;
            """,
            (last_processed_block - 1,),
        )
    conn.commit()
except Exception as e:
    try:
        conn.rollback()
    except Exception:
        pass
    logger.error(
        "Unable to initialize the database checkpoint. Apply create_tables.sql "
        f"and verify sync_state permissions: {sanitize_database_error(e)}"
    )
    sys.exit(1)
finally:
    if cur is not None:
        try:
            cur.close()
        except Exception:
            pass
    try:
        conn.close()
    except Exception:
        pass

# Wait for the Ethereum node to be in sync before indexing
while bool(web3.eth.syncing):
    logger.info("Waiting for Ethereum node to finish synchronizing… (retrying in 5 minutes)")
    time.sleep(300)

logger.info("Ethereum node is synchronized.")


def insert_txs_from_block(block, cursor, address_filter=None):
    """Parses and inserts native ETH and ERC-20 transfer transactions from a block."""
    block_id = block["number"]
    tx_time = block["timestamp"]
    inserted_transactions = 0

    for tx in block.transactions:
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
        contract_to = ""
        contract_value = ""

        # Parse ERC-20 transfer method (0xa9059cbb + 32-byte recipient + 32-byte amount)
        if input_hex.startswith("0xa9059cbb"):
            contract_to = input_hex[10:-64]
            contract_value = input_hex[74:]

        # Filter out malformed contract transfer inputs
        if len(contract_to) > 128:
            logger.info(
                f"Skipping tx {tx_hash}: unexpected contract_to length ({len(contract_to)})"
            )
            contract_to = ""
            contract_value = ""

        if address_filter is not None and not transaction_matches_filter(
            address_filter, tx_from, tx_to, contract_to
        ):
            continue

        tx_receipt = web3.eth.get_transaction_receipt(tx["hash"])
        gas = tx_receipt["gasUsed"]

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
        inserted_transactions += 1

    return inserted_transactions


# Main synchronization loop
while True:
    try:
        conn = connect_database(dbname)
        conn.autocommit = False
    except Exception as e:
        logger.error(
            f"Unable to connect to database: {sanitize_database_error(e)}"
        )
        time.sleep(int(polling_period))
        continue

    cur = conn.cursor()

    try:
        if address_filter_enabled:
            refreshed_addresses = load_monitored_addresses(address_filter_file)
            if refreshed_addresses != monitored_addresses:
                monitored_addresses = refreshed_addresses
                logger.info(
                    f"Reloaded {len(monitored_addresses)} monitored addresses "
                    f"from '{address_filter_file}'"
                )

        cur.execute(
            """
            SELECT GREATEST(
                (SELECT MAX(block) FROM public.ethtxs),
                (SELECT last_block FROM public.sync_state WHERE singleton = TRUE)
            );
            """
        )
        max_block_in_db = cur.fetchone()[0]

        # On first start with an empty database, index from START_BLOCK
        if max_block_in_db is None:
            max_block_in_db = int(start_block) - 1

        end_block = int(web3.eth.block_number) - int(confirmation_blocks)

        logger.info(
            f"Current best block in index: {max_block_in_db}; in Ethereum chain: {end_block}"
        )

        for block_height in range(max_block_in_db + 1, end_block):
            block = web3.eth.get_block(block_height, True)
            inserted_transactions = insert_txs_from_block(
                block,
                cur,
                monitored_addresses if address_filter_enabled else None,
            )
            cur.execute(
                """
                INSERT INTO public.sync_state(singleton, last_block)
                VALUES (TRUE, %s)
                ON CONFLICT (singleton) DO UPDATE
                SET last_block = EXCLUDED.last_block;
                """,
                (block_height,),
            )
            conn.commit()
            if len(block.transactions) > 0:
                logger.info(
                    f"Block {block_height} with {len(block.transactions)} transactions processed"
                )
            else:
                logger.info(f"Block {block_height} contains no transactions")

            if address_filter_enabled:
                logger.info(
                    f"Address filter stored {inserted_transactions} transactions "
                    f"from block {block_height}"
                )
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error(f"Error during synchronization pass: {sanitize_database_error(e)}")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    time.sleep(int(polling_period))
