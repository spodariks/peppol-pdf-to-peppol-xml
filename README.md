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
- Known UBL sibling groups are re-ordered according to their Peppol tree order

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
