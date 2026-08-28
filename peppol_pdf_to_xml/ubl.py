"""Lossless UBL mutations and parent-specific Peppol BIS Billing ordering."""
from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS = {"cbc": CBC, "cac": CAC}
for prefix, uri in {"cbc": CBC, "cac": CAC, "ext": EXT}.items(): ET.register_namespace(prefix, uri)
Q = lambda namespace, name: f"{{{namespace}}}{name}"
def _tags(namespace: str, names: str) -> list[str]: return [Q(namespace, name) for name in names.split()]

# UBL 2.1 sequence maps for all aggregates handled or populated by the converter.
# The Peppol Invoice/CreditNote trees use these UBL parent-specific sequences;
# there is intentionally no global element order.
DOCUMENT_ORDER = _tags(EXT, "UBLExtensions") + _tags(CBC, "UBLVersionID CustomizationID ProfileID ProfileExecutionID ID CopyIndicator UUID IssueDate IssueTime DueDate InvoiceTypeCode Note TaxPointDate DocumentCurrencyCode TaxCurrencyCode PricingCurrencyCode PaymentCurrencyCode PaymentAlternativeCurrencyCode AccountingCostCode AccountingCost LineCountNumeric BuyerReference") + _tags(CAC, "InvoicePeriod OrderReference BillingReference DespatchDocumentReference ReceiptDocumentReference StatementDocumentReference OriginatorDocumentReference ContractDocumentReference AdditionalDocumentReference ProjectReference Signature AccountingSupplierParty AccountingCustomerParty PayeeParty BuyerCustomerParty TaxRepresentativeParty TaxTotal WithholdingTaxTotal AllowanceCharge PrepaidPayment PaymentMeans PaymentTerms PaymentExchangeRate PaymentAlternativeExchangeRate TaxExchangeRate PricingExchangeRate PaymentAlternativeExchangeRate LegalMonetaryTotal InvoiceLine CreditNoteLine")
ORDERS: dict[str, list[str]] = {
    "Invoice": DOCUMENT_ORDER, "CreditNote": DOCUMENT_ORDER,
    "OrderReference": _tags(CBC, "ID SalesOrderID CopyIndicator UUID IssueDate DocumentTypeCode DocumentType") + _tags(CAC, "DocumentReference"),
    "AdditionalDocumentReference": _tags(CBC, "ID CopyIndicator UUID IssueDate IssueTime DocumentTypeCode DocumentType DocumentStatusCode DocumentDescription") + _tags(CAC, "Attachment ValidityPeriod IssuerParty ResultOfVerification"),
    "Attachment": _tags(CBC, "EmbeddedDocumentBinaryObject EmbeddedDocument URI") + _tags(CAC, "ExternalReference"),
    "ExternalReference": _tags(CBC, "URI DocumentHash HashAlgorithmMethod ExpiryDate ExpiryTime MimeCode FormatCode EncodingCode CharacterSetCode FileName") + _tags(CAC, "ValidationResult"),
    "AccountingSupplierParty": _tags(CBC, "CustomerAssignedAccountID AdditionalAccountID DataSendingCapability") + _tags(CAC, "Party SellerContact"),
    "AccountingCustomerParty": _tags(CBC, "CustomerAssignedAccountID SupplierAssignedAccountID AdditionalAccountID DataSendingCapability") + _tags(CAC, "Party DeliveryContact AccountingContact BuyerContact"),
    "Party": _tags(CBC, "MarkCareIndicator MarkAttentionIndicator WebsiteURI LogoReference EndpointID IndustryClassificationCode") + _tags(CAC, "PartyIdentification PartyName Language PostalAddress PhysicalLocation PartyTaxScheme PartyLegalEntity Contact Person AgentParty ServiceProviderParty PowerOfAttorney FinancialAccount"),
    "PartyIdentification": _tags(CBC, "ID"), "PartyName": _tags(CBC, "Name"),
    "PartyTaxScheme": _tags(CBC, "RegistrationName CompanyID ExemptionReason") + _tags(CAC, "TaxScheme"),
    "PartyLegalEntity": _tags(CBC, "RegistrationName CompanyID RegistrationDate SoleProprietorshipIndicator CompanyLegalForm") + _tags(CAC, "CorporateRegistrationScheme HeadOfficeParty ShareholderParty"),
    "Contact": _tags(CBC, "ID Name Telephone Telefax ElectronicMail Note OtherContactType") + _tags(CAC, "OtherCommunication"),
    "Address": _tags(CBC, "ID AddressTypeCode AddressFormatCode Postbox StreetName AdditionalStreetName BlockName BuildingName BuildingNumber InhouseMail Department MarkAttention MarkCare PlotIdentification CitySubdivisionName CityName PostalZone CountrySubentity CountrySubentityCode Region District") + _tags(CAC, "AddressLine Country LocationCoordinate"),
    "AddressLine": _tags(CBC, "Line"), "Country": _tags(CBC, "IdentificationCode Name"),
    "TaxScheme": _tags(CBC, "ID Name TaxTypeCode CurrencyCode") + _tags(CAC, "JurisdictionRegion"),
    "PaymentMeans": _tags(CBC, "ID PaymentMeansCode PaymentDueDate PaymentChannelCode InstructionID InstructionNote PaymentID CardTypeCode") + _tags(CAC, "PayerFinancialAccount PayeeFinancialAccount PaymentMandate"),
    "FinancialAccount": _tags(CBC, "ID Name AliasName AccountTypeCode AccountFormatCode CurrencyCode PaymentNote") + _tags(CAC, "FinancialInstitutionBranch Country"),
    "PaymentTerms": _tags(CBC, "ID PaymentMeansID PrepaidPaymentReferenceID Note PenaltySurchargePercent Amount PenaltyAmount PaymentDueDate") + _tags(CAC, "SettlementPeriod"),
    "AllowanceCharge": _tags(CBC, "ID ChargeIndicator AllowanceChargeReasonCode AllowanceChargeReason MultiplierFactorNumeric PrepaidIndicator SequenceNumeric Amount BaseAmount PerUnitAmount") + _tags(CAC, "AccountingCostCode AccountingCost TaxCategory PaymentMeans"),
    "TaxTotal": _tags(CBC, "TaxAmount RoundingAmount") + _tags(CAC, "TaxSubtotal"),
    "TaxSubtotal": _tags(CBC, "TaxableAmount TaxAmount CalculationSequenceNumeric TransactionCurrencyTaxAmount Percent BaseUnitMeasure PerUnitAmount TierRange TierRate") + _tags(CAC, "TaxCategory"),
    "TaxCategory": _tags(CBC, "ID Name Percent BaseUnitMeasure PerUnitAmount TaxExemptionReasonCode TaxExemptionReason TierRange TierRate") + _tags(CAC, "TaxScheme"),
    "LegalMonetaryTotal": _tags(CBC, "LineExtensionAmount TaxExclusiveAmount TaxInclusiveAmount AllowanceTotalAmount ChargeTotalAmount PrepaidAmount PayableRoundingAmount PayableAmount"),
    "InvoiceLine": _tags(CBC, "ID UUID Note InvoicedQuantity LineExtensionAmount TaxPointDate AccountingCost PaymentPurposeCode FreeOfChargeIndicator") + _tags(CAC, "InvoicePeriod OrderLineReference DespatchLineReference ReceiptLineReference DocumentReference PricingReference OriginatorParty Delivery PartyItemLocation AllowanceCharge TaxTotal WithholdingTaxTotal Item Price DeliveryTerms SubInvoiceLine"),
    "CreditNoteLine": _tags(CBC, "ID UUID Note CreditedQuantity LineExtensionAmount TaxPointDate AccountingCost PaymentPurposeCode FreeOfChargeIndicator") + _tags(CAC, "CreditNotePeriod OrderLineReference DespatchLineReference ReceiptLineReference DocumentReference PricingReference OriginatorParty Delivery PartyItemLocation AllowanceCharge TaxTotal Item Price DeliveryTerms SubCreditNoteLine"),
    "Item": _tags(CBC, "Description PackSizeNumeric PackSizeText CatalogueIndicator Name HazardousRiskIndicator AdditionalInformation Keyword") + _tags(CAC, "BuyersItemIdentification SellersItemIdentification ManufacturersItemIdentification StandardItemIdentification CatalogueItemIdentification AdditionalItemIdentification CatalogueDocumentReference ItemSpecificationDocumentReference OriginCountry CommodityClassification TransactionConditions HazardousItem ClassifiedTaxCategory InformationContent Dimension"),
    "Price": _tags(CBC, "PriceAmount BaseQuantity PriceTypeCode PriceType Description") + _tags(CAC, "AllowanceCharge ValidityPeriod PriceList"),
    "Delivery": _tags(CBC, "ID Quantity MinimumQuantity MaximumQuantity ActualDeliveryDate ActualDeliveryTime LatestDeliveryDate LatestDeliveryTime TrackingID") + _tags(CAC, "DeliveryAddress DeliveryLocation AlternativeDeliveryLocation RequestedDeliveryPeriod PromisedDeliveryPeriod EstimatedDeliveryPeriod CarrierParty DeliveryParty NotifyParty Despatch"),
}
# UBL reuses the Address aggregate sequence under these parent element names.
for _address_parent in ("PostalAddress", "DeliveryAddress", "RegistrationAddress"):
    ORDERS[_address_parent] = ORDERS["Address"]
def parse(xml: bytes) -> ET.Element: return ET.fromstring(xml)
def serialize(root: ET.Element) -> bytes: return ET.tostring(root, encoding="utf-8", xml_declaration=True)
def _name(tag: str) -> str: return tag.rsplit("}", 1)[-1]
def _reorder(parent: ET.Element, order: list[str]) -> None:
    rank = {tag: index for index, tag in enumerate(order)}; original = list(parent)
    known = sorted((child for child in original if child.tag in rank), key=lambda child: rank[child.tag])
    if known:
        replacement = iter(known)
        parent[:] = [next(replacement) if child.tag in rank else child for child in original]
def enforce_peppol_order(root: ET.Element) -> None:
    """Recursively order only siblings for their own UBL aggregate parent."""
    for parent in root.iter():
        if order := ORDERS.get(_name(parent.tag)): _reorder(parent, order)
def set_references(root: ET.Element, po_number: str | None, buyer_reference: str | None) -> bool:
    changed = False
    if buyer_reference and root.find("cbc:BuyerReference", NS) is None:
        ET.SubElement(root, Q(CBC, "BuyerReference")).text = buyer_reference; changed = True
    if po_number and root.find("cac:OrderReference", NS) is None:
        order = ET.SubElement(root, Q(CAC, "OrderReference")); ET.SubElement(order, Q(CBC, "ID")).text = po_number; changed = True
    enforce_peppol_order(root); return changed
def set_invoice_number_as_buyer_reference(root: ET.Element) -> bool:
    if root.find("cbc:BuyerReference", NS) is not None: return False
    invoice_id = root.find("cbc:ID", NS)
    if invoice_id is None or not (invoice_id.text or "").strip(): return False
    ET.SubElement(root, Q(CBC, "BuyerReference")).text = invoice_id.text.strip(); enforce_peppol_order(root); return True
def normalize_prepaid_amount(root: ET.Element) -> bool:
    changed = False
    for node in root.findall("cac:LegalMonetaryTotal/cbc:PrepaidAmount", NS):
        try: value = Decimal((node.text or "").strip())
        except InvalidOperation: continue
        if value < 0: node.text = format(-value, "f"); changed = True
    return changed
def embed_original_pdf(root: ET.Element, pdf: bytes, filename: str = "original-invoice.pdf") -> bool:
    """Embed the supplied source PDF once as a document-level attachment."""
    if not pdf: raise ValueError("Original PDF is required for a final XML")
    if any(node.get("mimeCode") == "application/pdf" for node in root.findall("cac:AdditionalDocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject", NS)): return False
    reference = ET.SubElement(root, Q(CAC, "AdditionalDocumentReference")); ET.SubElement(reference, Q(CBC, "ID")).text = filename
    attachment = ET.SubElement(reference, Q(CAC, "Attachment")); binary = ET.SubElement(attachment, Q(CBC, "EmbeddedDocumentBinaryObject"), {"mimeCode": "application/pdf", "filename": filename})
    binary.text = base64.b64encode(pdf).decode("ascii"); enforce_peppol_order(root); return True
