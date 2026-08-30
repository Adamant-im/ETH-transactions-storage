"""PostgreSQL connection and diagnostic helpers."""

import importlib
import re


POSTGRESQL_URI_PREFIXES = ("postgres://", "postgresql://")
URI_PASSWORD_PATTERN = re.compile(
    r"(?P<prefix>postgres(?:ql)?://[^\s:/@]+:)[^\s@]+(?=@)",
    re.IGNORECASE,
)
KEYWORD_PASSWORD_PATTERN = re.compile(
    r"(?P<prefix>password\s*=\s*)(?:'[^']*'|\"[^\"]*\"|[^\s]+)",
    re.IGNORECASE,
)


def connect_database(database_name):
    """Connects using either a database name or a PostgreSQL connection URI."""
    psycopg2 = importlib.import_module("psycopg2")
    if database_name.startswith(POSTGRESQL_URI_PREFIXES):
        return psycopg2.connect(database_name)
    return psycopg2.connect(database=database_name)


def sanitize_database_error(error):
    """Redacts passwords from PostgreSQL errors before they are logged."""
    message = str(error)
    message = URI_PASSWORD_PATTERN.sub(r"\g<prefix>***", message)
    return KEYWORD_PASSWORD_PATTERN.sub(r"\g<prefix>***", message)
