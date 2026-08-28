"""UBL mutations that preserve the relevant Peppol child-element ordering."""

from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS = {"cbc": CBC, "cac": CAC}
for prefix, uri in {"cbc": CBC, "cac": CAC, "ext": EXT}.items():
    ET.register_namespace(prefix, uri)

Q = lambda namespace, name: f"{{{namespace}}}{name}"

# UBL 2.1 Invoice ordering for the top-level children this project creates/moves.
INVOICE_ORDER = [
    Q(EXT, "UBLExtensions"), Q(CBC, "UBLVersionID"), Q(CBC, "CustomizationID"), Q(CBC, "ProfileID"),
    Q(CBC, "ID"), Q(CBC, "IssueDate"), Q(CBC, "DueDate"), Q(CBC, "InvoiceTypeCode"), Q(CBC, "Note"),
    Q(CBC, "DocumentCurrencyCode"), Q(CBC, "BuyerReference"), Q(CAC, "OrderReference"),
    Q(CAC, "AdditionalDocumentReference"), Q(CAC, "AccountingSupplierParty"), Q(CAC, "AccountingCustomerParty"),
    Q(CAC, "TaxTotal"), Q(CAC, "LegalMonetaryTotal"), Q(CAC, "InvoiceLine"),
]
LEGAL_TOTAL_ORDER = [Q(CBC, "LineExtensionAmount"), Q(CBC, "TaxExclusiveAmount"), Q(CBC, "TaxInclusiveAmount"), Q(CBC, "AllowanceTotalAmount"), Q(CBC, "ChargeTotalAmount"), Q(CBC, "PrepaidAmount"), Q(CBC, "PayableRoundingAmount"), Q(CBC, "PayableAmount")]


def parse(xml: bytes) -> ET.Element:
    return ET.fromstring(xml)


def serialize(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _reorder(parent: ET.Element, order: list[str]) -> None:
    rank = {tag: i for i, tag in enumerate(order)}
    original = list(parent)
    known = sorted((child for child in original if child.tag in rank), key=lambda child: rank[child.tag])
    if not known:
        return
    iterator = iter(known)
    parent[:] = [next(iterator) if child.tag in rank else child for child in original]


def enforce_peppol_order(root: ET.Element) -> None:
    """Order known sibling groups; never drop or invent invoice values."""
    _reorder(root, INVOICE_ORDER)
    for total in root.findall("cac:LegalMonetaryTotal", NS):
        _reorder(total, LEGAL_TOTAL_ORDER)


def set_references(root: ET.Element, po_number: str | None, buyer_reference: str | None) -> bool:
    """Apply only extracted source values; PO takes BT-13, explicit reference BT-10."""
    changed = False
    if buyer_reference and not root.find("cbc:BuyerReference", NS):
        node = ET.Element(Q(CBC, "BuyerReference"))
        node.text = buyer_reference
        root.append(node)
        changed = True
    if po_number and not root.find("cac:OrderReference", NS):
        order = ET.Element(Q(CAC, "OrderReference"))
        identifier = ET.SubElement(order, Q(CBC, "ID"))
        identifier.text = po_number
        root.append(order)
        changed = True
    enforce_peppol_order(root)
    return changed


def set_invoice_number_as_buyer_reference(root: ET.Element) -> bool:
    """The documented fallback for BT-10 when no PO or explicit reference exists."""
    if root.find("cbc:BuyerReference", NS) is not None:
        return False
    invoice_id = root.find("cbc:ID", NS)
    if invoice_id is None or not (invoice_id.text or "").strip():
        return False
    reference = ET.Element(Q(CBC, "BuyerReference"))
    reference.text = invoice_id.text.strip()
    root.append(reference)
    enforce_peppol_order(root)
    return True


def normalize_prepaid_amount(root: ET.Element) -> bool:
    """Turn a negative BT-113 into its absolute value without altering other totals."""
    changed = False
    for node in root.findall("cac:LegalMonetaryTotal/cbc:PrepaidAmount", NS):
        try:
            value = Decimal((node.text or "").strip())
        except InvalidOperation:
            continue
        if value < 0:
            node.text = format(-value, "f")
            changed = True
    return changed


def embed_original_pdf(root: ET.Element, pdf: bytes, filename: str = "original-invoice.pdf") -> bool:
    """Embed the supplied original PDF once as a UBL attached document."""
    if not pdf:
        raise ValueError("Original PDF is required for a final XML")
    for attachment in root.findall("cac:AdditionalDocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject", NS):
        if attachment.get("mimeCode") == "application/pdf":
            return False
    reference = ET.Element(Q(CAC, "AdditionalDocumentReference"))
    ET.SubElement(reference, Q(CBC, "ID")).text = filename
    attachment = ET.SubElement(reference, Q(CAC, "Attachment"))
    binary = ET.SubElement(attachment, Q(CBC, "EmbeddedDocumentBinaryObject"), {"mimeCode": "application/pdf", "filename": filename})
    binary.text = base64.b64encode(pdf).decode("ascii")
    root.append(reference)
    enforce_peppol_order(root)
    return True
