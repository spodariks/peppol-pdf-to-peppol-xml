"""Small, dependency-free client for Peppol Validator's public API."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VALIDATOR_URL = "https://peppolvalidator.com/api/v1/validate"


class ValidatorUnavailable(RuntimeError):
    """The remote validator could not provide a result."""


@dataclass(frozen=True)
class ValidationError:
    rule: str | None
    message: str
    location: str | None
    severity: str = "error"

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> "ValidationError":
        return cls(value.get("rule"), value.get("message", ""), value.get("location"), value.get("severity", "error"))


@dataclass(frozen=True)
class ValidationResult:
    status: str
    errors: tuple[ValidationError, ...]
    warnings: tuple[ValidationError, ...]
    raw: dict[str, Any]

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "ValidationResult":
        return cls(
            status=payload.get("status", "error"),
            errors=tuple(ValidationError.from_api(e) for e in payload.get("errors", [])),
            warnings=tuple(ValidationError.from_api(e) for e in payload.get("warnings", [])),
            raw=payload,
        )


class PeppolValidatorClient:
    """POST raw XML, retrying only documented transient 500/503 responses."""

    def __init__(self, endpoint: str = VALIDATOR_URL, timeout_seconds: int = 30, sleep=time.sleep):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self._sleep = sleep

    def validate(self, xml: bytes) -> ValidationResult:
        if not xml:
            raise ValueError("Refusing to validate an empty XML document")
        last_error: Exception | None = None
        for attempt, delay in enumerate((0, 1, 2, 4)):
            if delay:
                self._sleep(delay)
            request = Request(self.endpoint, data=xml, method="POST", headers={"Content-Type": "application/xml", "Accept": "application/json"})
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return ValidationResult.from_api(payload)
            except HTTPError as exc:
                if exc.code not in (500, 503) or attempt == 3:
                    detail = exc.read().decode("utf-8", errors="replace")
                    raise ValidatorUnavailable(f"Validator HTTP {exc.code}: {detail}") from exc
                last_error = exc
            except (URLError, TimeoutError, json.JSONDecodeError) as exc:
                # Transport failures are not interpreted as invoice errors.
                if attempt == 3:
                    raise ValidatorUnavailable("Validator did not return usable JSON") from exc
                last_error = exc
        raise ValidatorUnavailable("Validator retries exhausted") from last_error
