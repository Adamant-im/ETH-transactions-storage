# Indexer for Ethereum to get transaction list by ETH address
# https://github.com/Adamant-im/ETH-transactions-storage
# By Artem Brunov, Aleksei Lebedev. (c) ADAMANT TECH LABS
# v. 1.1

from web3 import Web3
import psycopg2
import time
import sys
import logging
from secrets import DBHOST, DBNAME, DBUSER, DBPASS, DBPORT, WALLET

# Get postgre database name
#if len(sys.argv) < 2:
#    print('Add postgre database name as an argument')
#    exit()
#
#dbname = sys.argv[1]

# Connect to geth node
#web3 = Web3(Web3.IPCProvider("/home/geth/.ethereum/geth.ipc"))

# Or connect to parity node
#web3 = Web3(Web3.IPCProvider("/home/parity/.local/share/io.parity.ethereum/jsonrpc.ipc"))
web3 = Web3(Web3.IPCProvider("/home/ubuntu/.ethereum-classic/classic/geth.ipc"))

# Start logger
logger = logging.getLogger("EthIndexerLog")
logger.setLevel(logging.INFO)
lfh = logging.FileHandler("./ethindexer.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
lfh.setFormatter(formatter)
logger.addHandler(lfh)

try:
    conn = psycopg2.connect(
    host = DBHOST,
    database = DBNAME,
    user = DBUSER,
    password = DBPASS,
    port = DBPORT
    )
    #conn = psycopg2.connect("dbname=" + dbname)
    conn.autocommit = True
    logger.info("Connected to the database")
except:
    logger.error("Unable to connect to database")

# Delete last block as it may be not imparted in full
cur = conn.cursor()
cur.execute('DELETE FROM public.ethtxs WHERE block = (SELECT Max(block) from public.ethtxs)')
cur.close()
conn.close()

# Adds all transactions from Ethereum block
def insertion(blockid, tr):
    time = web3.eth.getBlock(blockid)['timestamp']
    for x in range(0, tr):
        trans = web3.eth.getTransactionByBlock(blockid, x)
        #logger.info(trans)
        txhash = trans['hash']
        value = trans['value']
        inputinfo = trans['input']
        # Check if transaction is a contract transfer
        #if (value == 0 and not inputinfo.startswith('0xa9059cbb')):
        #    continue
        fr = trans['from']
        to = trans['to']
        gasprice = trans['gasPrice']
        gas = web3.eth.getTransactionReceipt(trans['hash'])['gasUsed']
        contract_to = ''
        contract_value = inputinfo
        # Check if transaction is a contract transfer
        if inputinfo.startswith('0xa9059cbb'):
            contract_to = inputinfo[10:-64]
            contract_value = inputinfo[74:]
        
        if fr.lower() == WALLET.lower():
            cur.execute(
            'INSERT INTO public.ethtxs(time, txfrom, txto, value, gas, gasprice, block, txhash, contract_to, contract_value) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (time, fr, to, value, gas, gasprice, blockid, txhash, contract_to, contract_value))
            logger.info("%s %s" % (blockid, fr))

# Fetch all of new (not in index) Ethereum blocks and add transactions to index
while True:
    try:
        conn = psycopg2.connect(
        host = DBHOST,
        database = DBNAME,
        user = DBUSER,
        password = DBPASS,
        port = DBPORT
        )
        #conn = psycopg2.connect("dbname=" + dbname)
        conn.autocommit = True
    except:
        logger.error("Unable to connect to database")

    cur = conn.cursor()

    cur.execute('SELECT Max(block) from public.ethtxs')
    maxblockindb = cur.fetchone()[0]
    # On first start, we index transactions from a block number you indicate. 46146 is a sample.
    if maxblockindb is None:
        #maxblockindb = 46146
        maxblockindb = 3923978
   

    endblock = int(web3.eth.blockNumber)

    logger.info('Current best block in index: ' + str(maxblockindb) + '; in Ethereum chain: ' + str(endblock))

    for block in range(maxblockindb + 1, endblock):
        transactions = web3.eth.getBlockTransactionCount(block)
        if transactions > 0:
            insertion(block, transactions)
        else:
            logger.info('Block ' + str(block) + ' does not contain transactions')
    cur.close()
    conn.close()
    time.sleep(20)
