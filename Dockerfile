FROM python:3.11-slim

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /eth-storage

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY package.json address_filter.py database.py ethsync.py ethtest.py pgtest.py ./
COPY filter/addresses.txt.example ./filter/

ENV DB_NAME=index

ENTRYPOINT [ "python3", "./ethsync.py" ]
