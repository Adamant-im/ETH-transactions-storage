from web3 import Web3
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
#web3 = Web3(Web3.WebsocketProvider("ws://127.0.0.1:8546"))
print(web3.eth.blockNumber)
