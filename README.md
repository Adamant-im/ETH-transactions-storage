# ETH-transactions-storage
Indexer for getting transaction list for ETH address.

## Description
Standard Ethereum node lacks functionality to get transaction list for ETH address.
This project allows to run indexer over Ethereum DB and store store all transactions in one-query place. Iit is possible to obtain a history of every user|wallet in just a move, like Etherscan does.

## Prerequisites
geth (with currently synchronized chain)
Python 3.6
Postgresql 10.5

## Installation
Import wheels for python:

``` pip3 install web3
``` pip3 install psycopg2

<yourusername> - user who will run service.
<yourDB> - target DataBase. Change the DB name in two strings in the script file.
Create Postgres user for <yourusername>:
	
	createuser -s <yourusername>
	
In this example we create superuser.You can use your own grants.

Create a table in Postgres:

	psql -f create_table.sql <yourDB>

Run the script.

	python3.6 you/path/to/script/ethsync.py <yourDB>

Or use ethstorage.service to run as a deamon. Change string 

	ExecStart=/usr/bin/python3.6 you/path/to/script/ethsync.py <yourDB>

Put the file to	/lib/systemd/system. Then

	systemctl daemon-reload
	systemctl start ethstorage.service

Checking synchronization progress

	SELECT max(block) FROM ethtxs;



License
Copyright © 2017-2018 ADAMANT TECH LABS LP 
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

