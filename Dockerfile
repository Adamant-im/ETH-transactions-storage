# Container image for the Ethereum transaction indexer (ethsync.py).
# Published as ghcr.io/adamant-im/eth-transactions-storage
# Local build: docker build -t eth-transactions-storage:local .
#
# The image contains the indexer process only. PostgreSQL, PostgREST, and the
# Ethereum execution client stay separate services. No configuration, address
# list, or database data is baked in; everything is supplied at run time.

FROM python:3.11-slim

ARG IMAGE_VERSION=dev
ARG IMAGE_REVISION=unknown

LABEL org.opencontainers.image.title="ETH Transactions Storage" \
      org.opencontainers.image.description="Self-hosted Ethereum transaction indexer for native ETH and ERC-20 transfers with PostgreSQL and PostgREST" \
      org.opencontainers.image.source="https://github.com/Adamant-im/ETH-transactions-storage" \
      org.opencontainers.image.url="https://eth-indexer.docs.adamant.im" \
      org.opencontainers.image.documentation="https://eth-indexer.docs.adamant.im" \
      org.opencontainers.image.vendor="ADAMANT developer community" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${IMAGE_REVISION}"

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
