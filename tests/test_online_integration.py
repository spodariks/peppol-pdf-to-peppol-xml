"""Runs only when explicitly enabled; never fakes a validator PASS."""
import os
import unittest
from pathlib import Path

from peppol_pdf_to_xml.validator import PeppolValidatorClient, ValidatorUnavailable

@unittest.skipUnless(os.getenv("PEPPOL_ONLINE_INTEGRATION") == "1", "set PEPPOL_ONLINE_INTEGRATION=1 and PEPPOL_ONLINE_XML=/absolute/file.xml")
class OnlineValidatorIntegrationTests(unittest.TestCase):
    def test_remote_validator_returns_valid_for_supplied_known_good_xml(self):
        filename = os.getenv("PEPPOL_ONLINE_XML")
        if not filename: self.fail("PEPPOL_ONLINE_XML must name a known-good Peppol XML file")
        try:
            result = PeppolValidatorClient().validate(Path(filename).read_bytes())
        except (OSError, ValidatorUnavailable) as exc:
            self.skipTest(f"online validator unavailable: {exc}")
        self.assertEqual("valid", result.status, result.errors)
