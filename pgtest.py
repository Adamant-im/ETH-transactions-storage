from os import environ
from pathlib import Path
import sys

from dotenv import load_dotenv

from database import connect_database, sanitize_database_error

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

dbname = environ.get("DB_NAME") or "index"

try:
    print("Connecting to PostgreSQL database…")
    conn = connect_database(dbname)
    conn.autocommit = True
    print("Connected to the PostgreSQL database successfully")

    cur = conn.cursor()
    cur.execute("SELECT MAX(block) FROM public.ethtxs;")
    max_block = cur.fetchone()[0]
    print(f"Current MAX(block) in 'ethtxs': {max_block}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Unable to connect to PostgreSQL database: {sanitize_database_error(e)}")
    sys.exit(1)
