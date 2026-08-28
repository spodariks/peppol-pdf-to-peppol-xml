import base64
import unittest
from xml.etree import ElementTree as ET

from peppol_pdf_to_xml import ReferenceData, ValidationPipeline
from peppol_pdf_to_xml.ubl import CAC, CBC, NS
from peppol_pdf_to_xml.validator import ValidationResult

INVOICE = b'''<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"><cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID><cbc:ID>INV-42</cbc:ID><cac:LegalMonetaryTotal><cbc:PayableAmount currencyID="EUR">0.00</cbc:PayableAmount><cbc:PrepaidAmount currencyID="EUR">-12.50</cbc:PrepaidAmount></cac:LegalMonetaryTotal></Invoice>'''


class FakeValidator:
    def __init__(self, responses): self.responses = iter(responses); self.calls = []
    def validate(self, xml): self.calls.append(xml); return next(self.responses)


def result(status, errors=()):
    return ValidationResult(status, tuple(errors), (), {"status": status})


class PipelineTests(unittest.TestCase):
    def test_embeds_pdf_applies_reference_policy_and_passes(self):
        validator = FakeValidator([result("valid")])
        outcome = ValidationPipeline(validator).run(INVOICE, b"%PDF-test", ReferenceData(po_number="PO-7", explicit_buyer_reference="BUY-9"))
        root = ET.fromstring(outcome.xml)
        self.assertEqual("PASS", outcome.status)
        self.assertEqual("BUY-9", root.find("cbc:BuyerReference", NS).text)
        self.assertEqual("PO-7", root.find("cac:OrderReference/cbc:ID", NS).text)
        self.assertEqual("12.50", root.find("cac:LegalMonetaryTotal/cbc:PrepaidAmount", NS).text)
        attachment = root.find("cac:AdditionalDocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject", NS)
        self.assertEqual("application/pdf", attachment.get("mimeCode"))
        self.assertEqual(b"%PDF-test", base64.b64decode(attachment.text))

    def test_missing_buyer_reference_uses_invoice_number_before_validation(self):
        # The required BT-10 fallback is deterministic, so it is applied before the
        # first remote request rather than waiting for a rejectable BR-10 error.
        validator = FakeValidator([result("valid")])
        outcome = ValidationPipeline(validator).run(INVOICE, b"pdf", ReferenceData())
        self.assertEqual("PASS", outcome.status)
        self.assertEqual(1, len(validator.calls))
        self.assertIn(b"<cbc:BuyerReference>INV-42</cbc:BuyerReference>", outcome.xml)

    def test_unknown_rule_stops_without_inventing_data(self):
        from peppol_pdf_to_xml.validator import ValidationError
        validator = FakeValidator([result("invalid", [ValidationError("BR-16", "line missing", "/Invoice")])])
        outcome = ValidationPipeline(validator).run(INVOICE, b"pdf", ReferenceData())
        self.assertEqual("STOP", outcome.status)
        self.assertEqual(1, len(validator.calls))
        self.assertNotIn(b"InvoiceLine", outcome.xml)

    def test_validator_transport_failure_is_not_a_pass(self):
        from peppol_pdf_to_xml.validator import ValidatorUnavailable
        class OfflineValidator:
            def validate(self, _xml): raise ValidatorUnavailable("offline")
        outcome = ValidationPipeline(OfflineValidator()).run(INVOICE, b"pdf")
        self.assertEqual("VALIDATOR_ERROR", outcome.status)
        self.assertEqual("offline", outcome.validator_error)

    def test_ordering_places_buyer_reference_before_order_reference(self):
        validator = FakeValidator([result("valid")])
        xml = ValidationPipeline(validator).run(INVOICE, b"pdf", ReferenceData("PO", "BUY")).xml
        self.assertLess(xml.index(b"<cbc:BuyerReference"), xml.index(b"<cac:OrderReference"))
