# PEPPOL PDF -> XML Codex project

This project adds an automatic Peppol validation stage to the PDF-to-XML workflow.

Flow:

PDF -> extraction -> UBL 2.1 / Peppol BIS Billing 3.0 -> local checks ->
Peppol Validator API -> correction -> revalidation -> valid -> embedded PDF -> final XML.

The validation skill is in:
`.agents/skills/validating-peppol-invoices/SKILL.md`

The online validator documents:
https://peppolvalidator.com/developers
https://peppolvalidator.com/ai-agents
