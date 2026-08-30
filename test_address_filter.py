"""Tests for address-filter configuration and matching."""

import tempfile
import unittest
from pathlib import Path

from address_filter import (
    load_monitored_addresses,
    normalize_address,
    parse_boolean,
    transaction_matches_filter,
)


ADDRESS_ONE = "0x1111111111111111111111111111111111111111"
ADDRESS_TWO = "0x2222222222222222222222222222222222222222"


class AddressFilterTest(unittest.TestCase):
    def test_parse_boolean_accepts_documented_values(self):
        self.assertTrue(parse_boolean("TRUE", "TEST_VALUE"))
        self.assertTrue(parse_boolean("1", "TEST_VALUE"))
        self.assertFalse(parse_boolean("off", "TEST_VALUE"))
        self.assertFalse(parse_boolean("0", "TEST_VALUE"))

    def test_parse_boolean_rejects_unknown_value(self):
        with self.assertRaisesRegex(ValueError, "TEST_VALUE must be one of"):
            parse_boolean("enabled", "TEST_VALUE")

    def test_load_monitored_addresses_ignores_comments_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "addresses.txt"
            path.write_text(
                f"# Wallets\n{ADDRESS_ONE.upper().replace('0X', '0x')} # Main\n{ADDRESS_ONE}\n",
                encoding="utf-8",
            )

            self.assertEqual(load_monitored_addresses(path), frozenset({ADDRESS_ONE}))

    def test_load_monitored_addresses_rejects_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "addresses.txt"
            path.write_text("# No active addresses\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "contains no Ethereum addresses"):
                load_monitored_addresses(path)

    def test_load_monitored_addresses_reports_invalid_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "addresses.txt"
            path.write_text(f"{ADDRESS_ONE}\nnot-an-address\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "line 2"):
                load_monitored_addresses(path)

    def test_load_monitored_addresses_requires_0x_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "addresses.txt"
            path.write_text(f"{ADDRESS_ONE[2:]}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "line 1"):
                load_monitored_addresses(path)

    def test_normalize_address_handles_abi_encoded_recipient(self):
        encoded_address = f"{'0' * 24}{ADDRESS_TWO[2:]}"
        self.assertEqual(normalize_address(encoded_address), ADDRESS_TWO)

    def test_transaction_matches_all_supported_address_fields(self):
        monitored_addresses = frozenset({ADDRESS_ONE})
        encoded_address = f"{'0' * 24}{ADDRESS_ONE[2:]}"

        self.assertTrue(
            transaction_matches_filter(monitored_addresses, ADDRESS_ONE, ADDRESS_TWO, "")
        )
        self.assertTrue(
            transaction_matches_filter(monitored_addresses, ADDRESS_TWO, ADDRESS_ONE, "")
        )
        self.assertTrue(
            transaction_matches_filter(
                monitored_addresses, ADDRESS_TWO, ADDRESS_TWO, encoded_address
            )
        )
        self.assertFalse(
            transaction_matches_filter(monitored_addresses, ADDRESS_TWO, ADDRESS_TWO, "")
        )


if __name__ == "__main__":
    unittest.main()
