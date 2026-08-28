import base64
import unittest
from xml.etree import ElementTree as ET

from peppol_pdf_to_xml.latvia import PEPPOL_CUSTOMIZATION_ID, PEPPOL_PROFILE_ID, validate_latvian_requirements
from peppol_pdf_to_xml.ubl import CAC, CBC, NS, embed_original_pdf, enforce_peppol_order, normalize_prepaid_amount, parse, set_invoice_number_as_buyer_reference, set_references

INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CREDIT_NS = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
Q = lambda namespace, name: f"{{{namespace}}}{name}"

def document(kind=INVOICE_NS, document_id="INV-42"):
    root = ET.Element(Q(kind, "Invoice" if kind == INVOICE_NS else "CreditNote"))
    ET.SubElement(root, Q(CBC, "ID")).text = document_id
    return root

class UblOrderingTests(unittest.TestCase):
    def test_invoice_orders_nested_groups_using_their_own_sequences(self):
        root = document()
        party = ET.SubElement(ET.SubElement(root, Q(CAC, "AccountingSupplierParty")), Q(CAC, "Party"))
        ET.SubElement(party, Q(CAC, "Contact")); ET.SubElement(party, Q(CAC, "PartyName"))
        address = ET.SubElement(party, Q(CAC, "PostalAddress"))
        ET.SubElement(address, Q(CAC, "Country")); ET.SubElement(address, Q(CBC, "CityName")); ET.SubElement(address, Q(CBC, "StreetName"))
        line = ET.SubElement(root, Q(CAC, "InvoiceLine"))
        ET.SubElement(line, Q(CAC, "Price")); ET.SubElement(line, Q(CBC, "InvoicedQuantity")); ET.SubElement(line, Q(CBC, "ID")); ET.SubElement(line, Q(CAC, "Item"))
        enforce_peppol_order(root)
        self.assertEqual(["PartyName", "PostalAddress", "Contact"], [child.tag.rsplit('}', 1)[-1] for child in party])
        self.assertEqual(["StreetName", "CityName", "Country"], [child.tag.rsplit('}', 1)[-1] for child in address])
        self.assertEqual(["ID", "InvoicedQuantity", "Item", "Price"], [child.tag.rsplit('}', 1)[-1] for child in line])

    def test_credit_note_uses_credit_note_line_sequence(self):
        root = document(CREDIT_NS, "CN-9")
        line = ET.SubElement(root, Q(CAC, "CreditNoteLine"))
        ET.SubElement(line, Q(CAC, "Price")); ET.SubElement(line, Q(CBC, "CreditedQuantity")); ET.SubElement(line, Q(CBC, "ID")); ET.SubElement(line, Q(CAC, "Item"))
        enforce_peppol_order(root)
        self.assertEqual(["ID", "CreditedQuantity", "Item", "Price"], [child.tag.rsplit('}', 1)[-1] for child in line])

    def test_pdf_is_base64_and_in_correct_document_position(self):
        root = document(); ET.SubElement(root, Q(CAC, "AccountingSupplierParty"))
        embed_original_pdf(root, b"%PDF-1.7 original")
        attachment = root.find("cac:AdditionalDocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject", NS)
        self.assertEqual("application/pdf", attachment.get("mimeCode"))
        self.assertEqual(b"%PDF-1.7 original", base64.b64decode(attachment.text))
        tags = [node.tag.rsplit('}', 1)[-1] for node in root]
        self.assertLess(tags.index("AdditionalDocumentReference"), tags.index("AccountingSupplierParty"))

class BusinessRuleTests(unittest.TestCase):
    def test_buyer_reference_priority(self):
        po = document(); set_references(po, "PO-1", None)
        self.assertEqual("PO-1", po.findtext("cac:OrderReference/cbc:ID", namespaces=NS)); self.assertIsNone(po.find("cbc:BuyerReference", NS))
        explicit = document(); set_references(explicit, None, "BUY-1")
        self.assertEqual("BUY-1", explicit.findtext("cbc:BuyerReference", namespaces=NS)); self.assertIsNone(explicit.find("cac:OrderReference", NS))
        fallback = document(document_id="INV-FALLBACK"); self.assertTrue(set_invoice_number_as_buyer_reference(fallback))
        self.assertEqual("INV-FALLBACK", fallback.findtext("cbc:BuyerReference", namespaces=NS))

    def test_al00042200_negative_prepaid_becomes_positive_eur(self):
        root = document(); total = ET.SubElement(root, Q(CAC, "LegalMonetaryTotal")); amount = ET.SubElement(total, Q(CBC, "PrepaidAmount"), {"currencyID": "EUR"}); amount.text = "-66.42"
        self.assertTrue(normalize_prepaid_amount(root)); self.assertEqual("66.42", amount.text); self.assertEqual("EUR", amount.get("currencyID"))

class LatvianLayerTests(unittest.TestCase):
    def _latvian_document(self):
        root = document(); ET.SubElement(root, Q(CBC, "CustomizationID")).text = PEPPOL_CUSTOMIZATION_ID; ET.SubElement(root, Q(CBC, "ProfileID")).text = PEPPOL_PROFILE_ID
        supplier = ET.SubElement(root, Q(CAC, "AccountingSupplierParty")); party = ET.SubElement(supplier, Q(CAC, "Party")); address = ET.SubElement(party, Q(CAC, "PostalAddress")); country = ET.SubElement(address, Q(CAC, "Country")); ET.SubElement(country, Q(CBC, "IdentificationCode")).text = "LV"
        enforce_peppol_order(root); return root
    def test_lv_document_accepts_mandated_peppol_profile(self):
        result = validate_latvian_requirements(self._latvian_document()); self.assertTrue(result.applicable); self.assertEqual((), result.errors)
    def test_lv_document_reports_national_profile_requirement(self):
        root = self._latvian_document(); root.find("cbc:ProfileID", NS).text = "wrong"
        result = validate_latvian_requirements(root); self.assertEqual(["LV-NATIONAL-002"], [error.rule for error in result.errors])
    def test_non_latvian_supplier_is_outside_latvian_layer(self):
        root = self._latvian_document(); root.find("cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode", NS).text = "EE"
        result = validate_latvian_requirements(root); self.assertFalse(result.applicable); self.assertEqual((), result.errors)
