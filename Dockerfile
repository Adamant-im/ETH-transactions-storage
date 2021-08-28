FROM python:3.6-slim

RUN apt update -y
RUN apt install -y build-essential 
RUN apt install -y git
RUN pip3 install web3
RUN pip3 install psycopg2

RUN mkdir /eth-storage

COPY ./ethsync.py /eth-storage

ENV DB_NAME=yourDB

WORKDIR /eth-storage
ENTRYPOINT [ "python3.6", "./ethsync.py" ]
