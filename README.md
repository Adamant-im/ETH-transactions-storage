# Indexer for Ethereum to get transaction list by ETH address

Known Ethereum nodes lack functionality to get transaction list for ETH address (account). This Indexer allows to explore ETH and ERC20 transactions by Ethereum address and obtain a history of any user|wallet in just a move, like Etherscan does.

Indexer is written in Python. It works as a service in background:

- connects to Ethereum node (works well with openethereum, geth or parity, others are not tested)
- stores all transactions in Postgres database
- provides data for API to get transactions by address with postgrest

We've also found this [Indexer fork for mongodb](https://github.com/jin10086/ETH-transactions-storage), but didn't test it.

## Stored information

All indexed transactions includes (database field names shown):

- `time` is a transaction's timestamp
- `txfrom` sender's Ethereum address
- `txto` recipient's Ethereum address
- `value` stores amount of ETH transferred
- `gas` indicates `gasUsed`
- `gasprice` indicates `gasPrice`
- `block` is a transaction's block number
- `txhash` is a transaction's hash
- `contract_to` indicates recipient's Ethereum address in case of contract
- `contract_value` stores amount of ERC20 transaction in its tokens

To reduce storage requirements, Indexer stores only token transfer ERC20 transaction, started with `0xa9059cbb` in raw tx input.

An example:

```
{
  "time": 1576008898,
  "txfrom": "0x6B924750e56A674A2Ad01FBF09C7c9012f16f094",
  "txto": "0x1143E097e134F3407eF6B088672CCECE9A4f8CDD",
  "gas": 21000,
  "gasprice": 2500000000,
  "block": 9084957,
  "txhash": "\\xcf56a031dfc89f5a3686cd441ea97ae96a66f5809a4c8c1b370485a04fb37e0e",
  "value": 1200000000000000,
  "contract_to": "",
  "contract_value": ""
}
```

Refers to transaction 0xcf56a031dfc89f5a3686cd441ea97ae96a66f5809a4c8c1b370485a04fb37e0e.

## Ethereum Indexer's API

To get Ethereum transactions by address, Postgrest is used. It provides RESTful API to Postgres index database.

After index is created, you can use requests like

```
curl -k -X GET "http://localhost:3000/?and=(contract_to.eq.,or(txfrom.eq.0x6b924750e56a674a2ad01fbf09c7c9012f16f094,txto.eq.0x6b924750e56a674a2ad01fbf09c7c9012f16f094))&order=time.desc&limit=25"
```

The request will show 25 last transactions for Ethereum address 0x6b924750e56a674a2ad01fbf09c7c9012f16f094, ordered by timestamp. For API reference, see [Postgrest](https://postgrest.org/en/v5.2/api.html).

# Ethereum Indexer Setup

## Prerequisites

- geth or openethereum (with currently synchronized chain)
- Python 3.6
- Postgresql 10.5
- Postgrest for API
- nginx or other web server (in case of public API)

## Installation

### Ethereum Node

Make sure your Ethereum node is installed and is fully synced. In case of openethereum, you can check its API and best block height with the command:

```
curl --data '{"method":"eth_blockNumber","params":[],"id":1,"jsonrpc":"2.0"}' -H "Content-Type: application/json" -X POST localhost:8545
```

### Python modules

Install Python. Install python modules:

```
pip3 install web3
pip3 install psycopg2
```

### PostgreSQL

Install Postgres. Create Postgres user:

```
createuser -s <yourusername>
```

`<yourusername>` — user who will run service.

(As example we create superuser. You can use your own grants.)

Create database for Ethereum transaction index:

```
CREATE DATABASE index;
```

Create table using sql script `create_table.sql`:

```
psql -f create_table.sql <yourDB>
```

`<yourDB>` — target Postgres database.

Note, for case insensitive comparisons we use `citex` data type instead of `text`.

Remember to grant privileges to psql database and tables for users you need. Example:

```
\c index
GRANT ALL ON ethtxs TO api_user;
GRANT ALL ON aval TO api_user;
GRANT ALL ON max_block TO api_user;
GRANT ALL PRIVILEGES ON DATABASE index TO api_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO api_user;
```

### Ethereum transaction Indexer

`ethsync.py` is a script which makes Ethereum transactions index to get transactions by ETH address using API.

Log is stored in `/var/log/ethindexer.log`.

By default, Indexer connects to [Openethereum](https://github.com/openethereum/openethereum) node. You can also connect to other Ethereum node like geth:

``` python
# Connect to geth node
#web3 = Web3(Web3.IPCProvider("/home/geth/.ethereum/geth.ipc"))

# Or connect to openethereum node
web3 = Web3(Web3.IPCProvider("/home/parity/.local/share/openethereum/jsonrpc.ipc"))
```

Indexer can fetch transactions not from the beginning, but from special block number. It will speed up indexing process and reduce database size. If you want to indicate starting Ethereum block number, set it instead of default `10000000` value.

``` python
    if maxblockindb is None:
        maxblockindb = 10000000
```

For a reference:

- index size starting from 5,555,555 block to 9,000,000 is about 190 GB.
- index size starting from 11,000,000 block to 12,230,000 is about 83 GB.

First Indexer will store transactions starting from block you set. It will take a time. After that, it will check for new blocks every 20 seconds and update the index. If you want to change the interval, change the line:

```
    time.sleep(20)
```

To run the Indexer:

```
python3.6 you/path/to/script/ethsync.py <yourDB>
```

We recommend to run Indexer script `ethsync.py` as a background service. See `ethstorage.service` as an example. Before run, update the line:

```
ExecStart=/usr/bin/python3.6 you/path/to/script/ethsync.py <yourDB>
```

Put the file to `/lib/systemd/system`. Then register a service:

```
systemctl daemon-reload
systemctl start ethstorage.service
systemctl enable ethstorage.service
```

Note, indexing takes time. To check indexing process, get the last indexed block:

```
psql -d index -c 'SELECT MAX(block) FROM ethtxs;'
```

And compare to Ethereum node's best block.

### Transaction API with Postgrest

Install and [configure](https://postgrest.org/en/v5.2/install.html#configuration) Postgrest.
Here is an example to run API for user `api_user` connected to `index` database on 3000 port:

```
db-uri = "postgres://api_user@/index"
db-schema = "public"
db-anon-role = "api_user"
db-pool = 10
server-host = "127.0.0.1"
server-port = 3000
```

Make sure you add Postgrest in crontab for autostart on reboot:

```
@reboot cd /usr/share && /usr/bin/postgrest ./postgrest.conf
```
  
## Make Indexer's API public

If you need to provide public API, use any web server like nginx and setup proxy to Postgrest port in config:

```
location /ethtxs {
    proxy_pass http://127.0.0.1:3000;
}
location /aval {
    proxy_pass http://127.0.0.1:3000;
}
location /max_block {
    proxy_pass http://127.0.0.1:3000;
}

```

This way two endpoints will be available:

- `/ethtxs` used to fetch Ethereum transactions by address
- `/aval` returns status of service. Endpoint `aval` is a table with `status` field just to check API availability.
- `/max_block` returns max Ethereum indexed block

## API request examples

Get last 25 Ethereum transactions without ERC-20 transactions for address 0x1143e097e134f3407ef6b088672ccece9a4f8cdd:

```
https://ethnode1.adamant.im/ethtxs?and=(contract_to.eq.,or(txfrom.eq.0x1143e097e134f3407ef6b088672ccece9a4f8cdd,txto.eq.0x1143e097e134f3407ef6b088672ccece9a4f8cdd))&order=time.desc&limit=25

```

Get last 25 ERC-20 transactions without Ethereum transactions for address 0x1143e097e134f3407ef6b088672ccece9a4f8cdd:

```
https://ethnode1.adamant.im/ethtxs?and=(contract_to.neq.,or(txfrom.eq.0x1143e097e134f3407ef6b088672ccece9a4f8cdd,txto.eq.0x1143e097e134f3407ef6b088672ccece9a4f8cdd))&order=time.desc&limit=25

```

Get last 25 transactions for both ERC-20 and Ethereum for address 0x1143e097e134f3407ef6b088672ccece9a4f8cdd:

```
https://ethnode1.adamant.im/ethtxs?and=(or(txfrom.eq.0x1143e097e134f3407ef6b088672ccece9a4f8cdd,txto.eq.0x1143e097e134f3407ef6b088672ccece9a4f8cdd))&order=time.desc&limit=25

```

Zabbix API availability trigger examples:

```
{API for Ethereum transactions:system.run["curl -s https://ethnode1.adamant.im/aval | jq .[].status"].last()}<>1

{API for Ethereum transactions:system.run["curl -s --connect-timeout 7 https://ethnode1.adamant.im/max_block | jq .[].max"].change()}<1
```

# Dockerized and docker compose
by Guénolé de Cadoudal (guenoledc@yahoo.fr)

In the `docker-compose.yml` you find a configuration that show how this tool can be embedded in a docker configuration with the following processes:
- postgres db: to store the indexed data
- postgREST tool to expose the data as a REST api (see above comments)
- GETH node in POA mode. Can be Openethereum, or another node, but not tested
- EthSync tool (this tool)

The EthSync tool accepts the following env variables:
- DB_NAME: postgres url of the db
- ETH_URL: eth node url to reach the node. Supports websocket, http and ipc.
- START_BLOCK: the first block to synchronize from. Default is 1.
- CONFIRMATIONS_BLOCK: the number of blocks to leave out of the synch from the end. I.e., last block is current `blockNumber - CONFIRMATIONS_BLOCK`. Default is 0.
- PERIOD: Number of seconds between to synchronization. Default is 20 sec.

# License

Copyright © 2020-2021 ADAMANT Foundation
Copyright © 2017-2020 ADAMANT TECH LABS LP

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.
