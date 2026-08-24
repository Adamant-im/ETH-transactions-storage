FROM python:3.11-slim

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential libpq-dev git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /eth-storage

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ./

ENV DB_NAME=index

ENTRYPOINT [ "python3", "./ethsync.py" ]
