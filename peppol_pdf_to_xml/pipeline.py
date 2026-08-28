"""Validation/correction loop: safe deterministic fixes only, otherwise STOP."""

from __future__ import annotations

from dataclasses import dataclass

from .ubl import embed_original_pdf, enforce_peppol_order, normalize_prepaid_amount, parse, serialize, set_invoice_number_as_buyer_reference, set_references
from .validator import PeppolValidatorClient, ValidationResult


@dataclass(frozen=True)
class ReferenceData:
    po_number: str | None = None
    explicit_buyer_reference: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    status: str  # PASS, STOP, or VALIDATOR_ERROR
    xml: bytes
    validations: tuple[ValidationResult, ...]
    applied_fixes: tuple[str, ...]


class ValidationPipeline:
    def __init__(self, validator: PeppolValidatorClient, max_correction_rounds: int = 2):
        self.validator = validator
        self.max_correction_rounds = max_correction_rounds

    def run(self, generated_xml: bytes, original_pdf: bytes, references: ReferenceData = ReferenceData()) -> PipelineResult:
        root = parse(generated_xml)
        fixes: list[str] = []
        if set_references(root, references.po_number, references.explicit_buyer_reference):
            fixes.append("applied extracted PO/explicit Buyer Reference")
        if not references.po_number and not references.explicit_buyer_reference and set_invoice_number_as_buyer_reference(root):
            fixes.append("used Invoice Number as BT-10 fallback")
        if normalize_prepaid_amount(root):
            fixes.append("normalized negative BT-113 PrepaidAmount")
        embed_original_pdf(root, original_pdf)
        enforce_peppol_order(root)
        xml = serialize(root)
        results: list[ValidationResult] = []

        for correction_round in range(self.max_correction_rounds + 1):
            result = self.validator.validate(xml)
            results.append(result)
            if result.status == "valid":
                return PipelineResult("PASS", xml, tuple(results), tuple(fixes))
            if result.status != "invalid":
                return PipelineResult("VALIDATOR_ERROR", xml, tuple(results), tuple(fixes))
            # Never emit a changed but unvalidated document once the bounded
            # correction budget has been consumed.
            if correction_round == self.max_correction_rounds:
                return PipelineResult("STOP", xml, tuple(results), tuple(fixes))
            changed, labels = self._apply_error_fixes(root, result, references)
            if not changed:
                return PipelineResult("STOP", xml, tuple(results), tuple(fixes))
            fixes.extend(labels)
            enforce_peppol_order(root)
            xml = serialize(root)
        raise AssertionError("correction loop should always return")

    @staticmethod
    def _apply_error_fixes(root, result: ValidationResult, references: ReferenceData) -> tuple[bool, list[str]]:
        """Allowlisted fixes, gated by a validator error and available source data."""
        rules = {error.rule for error in result.errors}
        labels: list[str] = []
        changed = False
        # Peppol R003 reports a missing buyer/PO reference. Never synthesize a
        # buyer value: only the documented invoice-number fallback is permitted.
        if "PEPPOL-EN16931-R003" in rules and not references.po_number and not references.explicit_buyer_reference:
            if set_invoice_number_as_buyer_reference(root):
                changed = True
                labels.append("corrected PEPPOL-EN16931-R003 with Invoice Number fallback")
        # Prepaid value must never be negative; the source amount determines its absolute value.
        if any(rule in rules for rule in {"BR-CO-16", "BR-CO-17", "BR-CO-25"}):
            if normalize_prepaid_amount(root):
                changed = True
                labels.append("normalized negative BT-113 after validation error")
        return changed, labels
