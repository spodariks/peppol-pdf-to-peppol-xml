---
name: validating-peppol-invoices
description: Validate Peppol UBL XML invoices and credit notes against EN16931 and Peppol BIS Billing 3.0 using the Peppol Validator API. Use after generating or modifying any Peppol XML.
---

# Validating Peppol invoices

Validate every generated UBL invoice or credit note before release.

## API

POST:
`https://peppolvalidator.com/api/v1/validate`

Send raw XML with:
`Content-Type: application/xml`

No API key is required.

## Procedure

1. Read the generated XML.
2. POST the exact XML bytes to the API.
3. Parse JSON response.
4. If `status == "valid"`, continue.
5. If `status == "invalid"`, inspect every item in `errors`.
6. Use `rule`, `message`, and `location` (XPath) to identify the problem.
7. Fix the generator or XML only when the correction is supported by the source PDF and project rules.
8. Revalidate.
9. Repeat until valid or until an error cannot be resolved safely.
10. Never claim EC/Peppol validation PASS without an actual validator response.

Warnings do not equal errors. Preserve warnings in the final validation report.

## Supported documents

The API automatically detects UBL 2.1 Invoice and CreditNote and validates them against:
- CEN EN16931 BR-* rules
- Peppol BIS Billing 3.0 PEPPOL-EN16931-* rules

## Project-specific rules

Buyer reference priority:
1. PO number -> BT-13
2. Explicit Buyer Reference -> BT-10
3. Invoice number -> BT-10 fallback

Prepayment:
If the PDF contains `Parāds (+) / Priekšapmaksa (-)` and the value is negative,
use its absolute value as BT-113 PrepaidAmount.

UBL ordering:
Use the Peppol BIS Billing 3.0 tree separately for every UBL element.
Do not apply one global child-element order.

Finalization:
Only release the XML after local checks pass and the Peppol Validator reports `valid`.
