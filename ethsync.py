# Indexer for Ethereum to get transaction list by ETH address
# https://github.com/Adamant-im/ETH-transactions-storage
# By Artem Brunov, Aleksei Lebedev
# 2020-2021 ADAMANT Foundation
# 2017-2020 ADAMANT TECH LABS LP
# v1.2

from os import environ
from web3 import Web3
from web3.middleware import geth_poa_middleware
import psycopg2
import time
import sys
import logging
#from systemd.journal import JournalHandler

# Get env variables or set to default

dbname = environ.get("DB_NAME")
startBlock = environ.get("START_BLOCK") or "1"
confirmationBlocks = environ.get("CONFIRMATIONS_BLOCK") or "0"
nodeUrl = environ.get("ETH_URL")
pollingPeriod = environ.get("PERIOD") or "20"

if dbname == None:
    print('Add postgre database in env var DB_NAME')
    exit(2)

if nodeUrl == None:
    print('Add eth url in env var ETH_URL')
    exit(2)

# Connect to Ethereum node
if nodeUrl.startswith("http"):
    web3 = Web3(Web3.HTTPProvider(nodeUrl))
if nodeUrl.startswith("ws"):
    web3 = Web3(Web3.WebsocketProvider(nodeUrl)) # "ws://publicnode:8546"
if web3 == None:
    web3 = Web3(Web3.IPCProvider(nodeUrl)) # "/home/parity/.local/share/openethereum/jsonrpc.ipc"

web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Start logger
#logger = logging.getLogger("EthIndexerLog")
logger = logging.getLogger("eth-sync")
logger.setLevel(logging.INFO)

# File logger
#lfh = logging.FileHandler("/var/log/ethindexer.log")
lfh = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
lfh.setFormatter(formatter)
logger.addHandler(lfh)

# Systemd logger, if we want to user journalctl logs
# Install systemd-python and 
# decomment "#from systemd.journal import JournalHandler" up
#ljc = JournalHandler()
#formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#ljc.setFormatter(formatter)
#logger.addHandler(ljc)

try:
    logger.info("Trying to connect to "+ dbname)
    conn = psycopg2.connect(dbname)
    conn.autocommit = True
    logger.info("Connected to the database")
except:
    logger.error("Unable to connect to database")
    exit(1)

# Delete last block as it may be not imparted in full
cur = conn.cursor()
cur.execute('DELETE FROM public.ethtxs WHERE block = (SELECT Max(block) from public.ethtxs)')
cur.close()
conn.close()

# Wait for the node to be in sync before indexing
logger.info("Waiting Ethereum node to be in sync...")

while web3.eth.syncing != False:
    # Change with the time, in second, do you want to wait
    # before cheking again, default is 5 minutes
    time.sleep(300)

logger.info("Ethereum node is synced!")

# Adds all transactions from Ethereum block
def insertion(blockid, tr):
    time = web3.eth.getBlock(blockid)['timestamp']
    for x in range(0, tr):
        trans = web3.eth.getTransactionByBlock(blockid, x)
        # Save also transaction status, should be null if pre byzantium blocks
        status = bool(web3.eth.get_transaction_receipt(trans['hash']).status)
        txhash = trans['hash'].hex()
        value = trans['value']
        inputinfo = trans['input']
        # Check if transaction is a contract transfer
        if (value == 0 and not inputinfo.startswith('0xa9059cbb')):
            continue
        fr = trans['from']
        to = trans['to']
        gasprice = trans['gasPrice']
        gas = web3.eth.getTransactionReceipt(trans['hash'])['gasUsed']
        contract_to = ''
        contract_value = ''
        # Check if transaction is a contract transfer
        if inputinfo.startswith('0xa9059cbb'):
            contract_to = inputinfo[10:-64]
            contract_value = inputinfo[74:]
        # Correct contract transfer transaction represents '0x' + 4 bytes 'a9059cbb' + 32 bytes (64 chars) for contract address and 32 bytes for its value
        # Some buggy txs can break up Indexer, so we'll filter it
        if len(contract_to) > 128:
            logger.info('Skipping ' + str(txhash) + ' tx. Incorrect contract_to length: ' + str(len(contract_to)))
            contract_to = ''
            contract_value = ''
        cur.execute(
            'INSERT INTO public.ethtxs(time, txfrom, txto, value, gas, gasprice, block, txhash, contract_to, contract_value, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (time, fr, to, value, gas, gasprice, blockid, txhash, contract_to, contract_value, status))

# Fetch all of new (not in index) Ethereum blocks and add transactions to index
while True:
    try:
        conn = psycopg2.connect(dbname)
        conn.autocommit = True
    except:
        logger.error("Unable to connect to database")

    cur = conn.cursor()

    cur.execute('SELECT Max(block) from public.ethtxs')
    maxblockindb = cur.fetchone()[0]
    # On first start, we index transactions from a block number you indicate
    if maxblockindb is None:
        maxblockindb = int(startBlock)

    endblock = int(web3.eth.blockNumber) - int(confirmationBlocks)

    logger.info('Current best block in index: ' + str(maxblockindb) + '; in Ethereum chain: ' + str(endblock))

    for block in range(maxblockindb + 1, endblock):
        transactions = web3.eth.getBlockTransactionCount(block)
        if transactions > 0:
            insertion(block, transactions)
        else:
            logger.debug('Block ' + str(block) + ' does not contain transactions')
    cur.close()
    conn.close()
    time.sleep(int(pollingPeriod))
