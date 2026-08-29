"""Address-filter configuration and matching helpers."""

import re
from pathlib import Path


ETHEREUM_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def parse_boolean(value, variable_name):
    """Parses a boolean environment variable without ambiguous fallbacks."""
    normalized_value = value.strip().lower()
    if normalized_value in TRUE_VALUES:
        return True
    if normalized_value in FALSE_VALUES:
        return False
    raise ValueError(
        f"{variable_name} must be one of: "
        f"{', '.join(sorted(TRUE_VALUES | FALSE_VALUES))}"
    )


def normalize_address(value):
    """Returns a lowercase 0x-prefixed address or None for non-address values."""
    if value is None:
        return None

    normalized_value = str(value).strip().lower()
    if normalized_value.startswith("0x"):
        normalized_value = normalized_value[2:]

    # ABI-encoded addresses occupy a 32-byte word and are left-padded with zeros.
    if len(normalized_value) == 64 and normalized_value[:24] == "0" * 24:
        normalized_value = normalized_value[24:]

    candidate = f"0x{normalized_value}"
    if ETHEREUM_ADDRESS_PATTERN.fullmatch(candidate) is None:
        return None
    return candidate


def load_monitored_addresses(file_path):
    """Loads, validates, and normalizes monitored addresses from a text file."""
    path = Path(file_path).expanduser()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError(f"Unable to read address filter file '{path}': {error}") from error

    addresses = set()
    for line_number, line in enumerate(lines, start=1):
        value = line.partition("#")[0].strip()
        if not value:
            continue

        if ETHEREUM_ADDRESS_PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"Invalid Ethereum address in '{path}' at line {line_number}: {value}"
            )
        addresses.add(value.lower())

    if not addresses:
        raise ValueError(f"Address filter file '{path}' contains no Ethereum addresses")

    return frozenset(addresses)


def transaction_matches_filter(monitored_addresses, tx_from, tx_to, contract_to):
    """Checks native and ERC-20 sender, recipient, and contract addresses."""
    transaction_addresses = {
        normalize_address(tx_from),
        normalize_address(tx_to),
        normalize_address(contract_to),
    }
    transaction_addresses.discard(None)
    return not monitored_addresses.isdisjoint(transaction_addresses)
