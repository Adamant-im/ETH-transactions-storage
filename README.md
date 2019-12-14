# Indexer for Ethereum to get transaction list by ETH address
Known Ethereum nodes lack functionality to get transaction list for ETH address (account). Indexer allows to explore transactions by Ethereum address and obtain a history of every user|wallet in just a move, like Etherscan does.
Indexer is written in Python. It works as a service in background:
- connects to Ethereum node (works well with geth or parity, others are not tested)
- stores all transactions in Postgres database

## Stored information
All indexed transactions includes (database field names shown):
- `time` is a transaction's `timestamp`
- `fr` indicates `from` (sender) Ethereum address
- `to` indicates `to` (recepient) Ethereum address
- `value` stores `value` of ETH transaction
- `gas` indicates `gasUsed`
- `gasprice` indicates `gasPrice`
- `blockid` is a transaction's block number
- `txhash` is a transaction's `hash`
- `contract_to` indicates recepient's Ethereum address in case of contract
- `contract_value` stores `value` of ERC20 transaction in its tokens

## Details and configuration
Indexer script `ethsync.py` is recommended to be run as a background service. Log is stored in `/var/log/ethindexer.log`.

By default, indexer connects to parity Ethereum node. Check these lines for correct path to ipc before you start the service. You can also connect to other Ethereum node.

``` python
# Connect to geth node
#web3 = Web3(Web3.IPCProvider("/home/geth/.ethereum/geth.ipc"))

# Or connect to parity node
web3 = Web3(Web3.IPCProvider("/home/parity/.local/share/io.parity.ethereum/jsonrpc.ipc"))
```

Indexer may fetch transactions not from the beginnig, but from special block number. It will speed up indexing process and reduce database size. If you wand to indicate starting Ethereum block number, set it instead of default `46146` value.

``` python
    if maxblockindb is None:
        maxblockindb = 46146
```

For a reference, index size starting from 5,555,555 block to 9,000,000 is about 190 GB.

## Ethereum Indexer's API
To get Ethereum transactions by address, Postgrest is used. It provides RESTful API to Postgre index database.
After index is created, you can use requests like

```
curl -k -X GET "http://localhost:3000/?and=(contract_to.eq.,or(txfrom.eq.0x6b924750e56a674a2ad01fbf09c7c9012f16f094,txto.eq.0x6b924750e56a674a2ad01fbf09c7c9012f16f094))&order=time.desc&limit=25"
```

The request will show 25 last transactions for Ethereum address 0x6b924750e56a674a2ad01fbf09c7c9012f16f094, ordered by timestamp. For API reference, see [Postgrest](https://postgrest.org/en/v5.2/api.html).

# Setup

## Prerequisites
- geth or parity (with currently synchronized chain)
- Python 3.6
- Postgresql 10.5
- Postgrest
- nginx (in case of public API)

## Installation

### Node
Make sure your Ethereum node is installed and fully synced. In case of parity, you can check its API and best block height with the command:

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
Install Postgre. Create Postgres user '<yourusername>':

```
createuser -s <yourusername>
```
	
(As example we create superuser. You can use your own grants.)

Create table using sql script in the repository:

```
psql -f create_table.sql <yourDB>
```

`<yourusername>` — user who will run service. `<yourDB>` — target Postres database.

### Ethereum transaction Indexer

`ethsync.py` in the repository is a script which makes Ethereum transactions index to get transactions by ETH address using API. For configuration, see [#Details-and-configuration].

Run the Indexer.

```
python3.6 you/path/to/script/ethsync.py <yourDB>
```

Or use ethstorage.service to run as a deamon (recommended). You should correct the line:

```
ExecStart=/usr/bin/python3.6 you/path/to/script/ethsync.py <yourDB>
```

Put the file to	`/lib/systemd/system`. Then register a service:

```
systemctl daemon-reload
systemctl start ethstorage.service
```

Note, indexing takes time. To check indexing process, get the last indexed block:

```
psql -d index -c 'SELECT MAX(block) FROM ethtxs;'
```

And compare to Ethereum node's best block.

### Transaction API with Postgrest
Install and [configure](https://postgrest.org/en/v5.2/install.html#configuration) Postgrest. 
Here is an example for running API for user `api_user` connected to `index` database on 3000 port:

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
If you need to provide public API, use any webserver like nginx and setup proxy to Postgrest port in config:

```
location /ethtxs {
    proxy_pass http://127.0.0.1:3000;
}
location /aval {
    proxy_pass http://127.0.0.1:3000;
}

```

That way two endpoints will be available:
- `/ethtxs` used to fetch Ethereum transactions by address
- `/aval` returns status of service 

Example:
```
https://ethnode1.adamant.im/ethtxs?and=(contract_to.eq.,or(txfrom.eq.0x6b924750e56a674a2ad01fbf09c7c9012f16f094,txto.eq.0x6b924750e56a674a2ad01fbf09c7c9012f16f094))&order=time.desc&limit=25

```

Example:
```
https://ethnode1.adamant.im/aval

```

# License
Copyright © 2017-2019 ADAMANT TECH LABS LP

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

