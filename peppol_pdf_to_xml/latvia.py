"""Latvian national applicability checks, deliberately separate from Peppol.

Latvia has no national CIUS or extensions beyond EN 16931.  The two checks below
implement Cabinet Regulation No. 154's national adoption requirement for a
Latvian supplier in public-procurement use; they do not masquerade generic
Peppol business rules as Latvia-specific content rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET

from .ubl import NS

PEPPOL_CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
PEPPOL_PROFILE_ID = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

@dataclass(frozen=True)
class LatvianValidationIssue:
    rule: str
    message: str

@dataclass(frozen=True)
class LatvianValidationResult:
    applicable: bool
    errors: tuple[LatvianValidationIssue, ...]

def validate_latvian_requirements(root: ET.Element) -> LatvianValidationResult:
    """Check the nationally mandated profile only when Seller country is LV."""
    country = root.findtext("cac:AccountingSupplierParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode", namespaces=NS)
    if (country or "").strip().upper() != "LV":
        return LatvianValidationResult(False, ())
    errors: list[LatvianValidationIssue] = []
    if (root.findtext("cbc:CustomizationID", namespaces=NS) or "").strip() != PEPPOL_CUSTOMIZATION_ID:
        errors.append(LatvianValidationIssue("LV-NATIONAL-001", "Latvian supplier documents within the national scope must declare Peppol BIS Billing 3.0 CustomizationID."))
    if (root.findtext("cbc:ProfileID", namespaces=NS) or "").strip() != PEPPOL_PROFILE_ID:
        errors.append(LatvianValidationIssue("LV-NATIONAL-002", "Latvian supplier documents within the national scope must declare the Peppol Billing 01 ProfileID."))
    return LatvianValidationResult(True, tuple(errors))
