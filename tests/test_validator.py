import unittest
from unittest.mock import patch

from peppol_pdf_to_xml.validator import PeppolValidatorClient


class Response:
    def __init__(self, payload): self.payload = payload
    def read(self): return self.payload
    def __enter__(self): return self
    def __exit__(self, *_): return False


class ValidatorClientTests(unittest.TestCase):
    @patch("peppol_pdf_to_xml.validator.urlopen")
    def test_posts_raw_xml_and_parses_rule_and_xpath(self, urlopen):
        urlopen.return_value = Response(b'{"status":"invalid","errors":[{"rule":"BR-10","message":"Buyer reference missing","location":"/Invoice/cbc:BuyerReference"}]}')
        result = PeppolValidatorClient(endpoint="https://validator.example/validate").validate(b"<Invoice/>")
        request = urlopen.call_args.args[0]
        self.assertEqual("POST", request.get_method())
        self.assertEqual("application/xml", request.get_header("Content-type"))
        self.assertEqual(b"<Invoice/>", request.data)
        self.assertEqual("BR-10", result.errors[0].rule)
        self.assertEqual("/Invoice/cbc:BuyerReference", result.errors[0].location)
