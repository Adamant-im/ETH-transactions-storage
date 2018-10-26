# ETH-transactions-storage
Able to store ETH transactions in separate DB

Main purpose.
You can store all ethereum transactions in one-query place. it is possible to obtain a history of every user|wallet in just a move.


Prerequisites
geth (with currently synchronized chain)
Python 3.6
Postgresql 10.5


Import wheels for python:
pip3 install web3
pip3 install psycopg2


<yourusername> - user who will run service.
<yourDB> - target DataBase. Change the DB name in two strings in the script file.
Create Postgres user for <yourusername>:
createuser -s <yourusername>
In this example we create superuser.You can use your own grants.

Create a table in Postgres:
psql -f create_table.sql <yourDB>

Run the script.
	python3.6 you/path/to/script/ethsync.py

Checking synchronization progress
	SELECT max(block) FROM ethtxs;

Additional info:
	1 almost all logs are commented in the script for increasing performance
	2 Script suggest that geth node is running via user ‘geth’
	3 ethindexer.service can be used for creating service


License
Copyright © 2017-2018 ADAMANT TECH LABS LP 
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

