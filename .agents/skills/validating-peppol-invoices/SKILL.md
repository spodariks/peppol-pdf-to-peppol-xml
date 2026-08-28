---
name: validating-peppol-invoices
description: Validate Peppol UBL XML invoices through Peppol Validator and make only explicitly allowed, source-backed deterministic corrections.
---

# Validating Peppol invoices

POST raw UBL XML to `https://peppolvalidator.com/api/v1/validate` with
`Content-Type: application/xml`. The JSON result contains `status` (`valid`,
`invalid`, or `error`) plus error `rule`, `message`, and XPath `location`.

## Required loop

1. Generate UBL 2.1 XML from extracted PDF data. Do not invent invoice values.
2. Apply source-backed project rules before validation:
   - PO number goes to BT-13 (`cac:OrderReference/cbc:ID`).
   - Explicit buyer reference goes to BT-10 (`cbc:BuyerReference`).
   - When neither exists, use the invoice number as BT-10.
   - A negative Prāds/Priekšapmaksa becomes the absolute BT-113 `PrepaidAmount`.
3. Embed the original PDF as `AdditionalDocumentReference` before final validation.
4. Validate. Inspect every error's rule and XPath location.
5. Fix only an allowlisted, deterministic issue with source evidence; e.g.
   `PEPPOL-EN16931-R003` may use the documented invoice-number fallback when
   there is no extracted PO or explicit Buyer Reference. Re-order the
   relevant UBL sibling tree; then validate again. Otherwise STOP and surface the
   original errors. Never make up parties, lines, taxes, identifiers, dates, or amounts.

The bundled pipeline implements this policy and retries only transient Validator
HTTP 500/503 failures. A `valid` result is PASS; `invalid` with no safe fix is STOP.
