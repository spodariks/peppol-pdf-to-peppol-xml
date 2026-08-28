# PEPPOL PDF → XML

This repository provides the validation and correction stage of a PDF-to-Peppol
UBL 2.1 conversion workflow.

```
extract PDF → generate UBL → embed original PDF → validate → safe fix → revalidate → PASS / STOP
```

It uses the public [`POST /api/v1/validate`](https://peppolvalidator.com/developers)
endpoint with raw XML (`Content-Type: application/xml`). No API key is used.

## Safety contract

The correction loop parses every returned error's rule, message, and XPath, but
only changes data through an allowlist. It never creates commercial facts.

- Extracted PO number → BT-13 (`cac:OrderReference/cbc:ID`)
- Explicit extracted Buyer Reference → BT-10 (`cbc:BuyerReference`)
- If both are absent → Invoice Number → BT-10
- Negative Prāds/Priekšapmaksa → absolute-value BT-113 (`PrepaidAmount`)
- The original input PDF is embedded as a Base64 `application/pdf` UBL attachment
- UBL children are re-ordered recursively with a sequence specific to each
  aggregate parent used by the converter (Invoice and CreditNote included)

All other validation errors result in `STOP`, preserving the XML and the API
error information for human/source-data resolution. Remote API `500` and `503`
responses are retried with bounded exponential backoff; other failures raise an
explicit validator error.

## Use

```python
from peppol_pdf_to_xml import ReferenceData, ValidationPipeline
from peppol_pdf_to_xml.validator import PeppolValidatorClient

pipeline = ValidationPipeline(PeppolValidatorClient())
result = pipeline.run(
    generated_xml=ubl_xml_bytes,
    original_pdf=original_pdf_bytes,
    references=ReferenceData(po_number=extracted_po, explicit_buyer_reference=extracted_reference),
)
if result.status != "PASS":
    raise RuntimeError(result.validations[-1].errors)
write_final_xml(result.xml)
```

The agent usage policy is in
[`.agents/skills/validating-peppol-invoices/SKILL.md`](.agents/skills/validating-peppol-invoices/SKILL.md).

## Test

```bash
python3 -m unittest discover -s tests -v
```

### Real online integration test

The normal suite never makes a network request. To exercise the real public API
with an independently known-good document, opt in explicitly:

```bash
PEPPOL_ONLINE_INTEGRATION=1 PEPPOL_ONLINE_XML=/absolute/path/to/known-good.xml \
  python3 -m unittest tests.test_online_integration -v
```

The test passes only when the returned JSON contains `status: "valid"`. Network,
HTTP, and malformed-JSON failures are reported as unavailable (not as PASS). The
same check is available for automation and exits non-zero for invalid XML:

```bash
python3 -m peppol_pdf_to_xml.integration /absolute/path/to/invoice.xml
```

## Latvian requirements

`peppol_pdf_to_xml.latvia` is a separate national-applicability layer. It is
applied only when the Seller postal country is `LV`; generic Peppol/EN 16931
checks remain the responsibility of the generic validator and are not labelled
as Latvian rules.

The repository contains no Latvian Schematron, no Latvia-specific Peppol rule
set, and no evidence of one having been removed. This matches the European
Commission's country profile: Latvia has **no national CIUS or extensions**
beyond EN 16931. The layer therefore checks the national legal adoption
requirement for the LV supplier/public-procurement scope: the document declares
the Peppol BIS Billing 3.0 CustomizationID and Billing 01 ProfileID. These are
reported as `LV-NATIONAL-001` and `LV-NATIONAL-002`, respectively, rather than
being presented as extra invoice-content rules.

Sources: [Cabinet Regulation No. 154, sections 2–4](https://likumi.lv/ta/id/306273),
[VID e-rēķini guidance](https://www.vid.gov.lv/lv/e-rekini), and the
[European Commission Latvia eInvoicing profile](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467108891/eInvoicing+in+Latvia).
Contract-specific extra fields remain outside this generic converter because
they depend on the particular procurement contract.
