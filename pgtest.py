from os import environ
import sys

import psycopg2

dbname = environ.get("DB_NAME") or "index"

try:
    print(f"Connecting to '{dbname}' database…")
    conn = psycopg2.connect(database=dbname)
    conn.autocommit = True
    print(f"Connected to the '{dbname}' database successfully")

    cur = conn.cursor()
    cur.execute("SELECT MAX(block) FROM public.ethtxs;")
    max_block = cur.fetchone()[0]
    print(f"Current MAX(block) in 'ethtxs': {max_block}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Unable to connect to '{dbname}' database: {e}")
    sys.exit(1)
