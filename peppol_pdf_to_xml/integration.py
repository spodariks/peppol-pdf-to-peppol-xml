"""Explicit, non-mocked online Peppol Validator integration path."""
from __future__ import annotations
import argparse
from pathlib import Path
from .validator import PeppolValidatorClient, ValidatorUnavailable

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an existing UBL XML with peppolvalidator.com")
    parser.add_argument("xml", type=Path, help="XML to POST exactly as stored")
    args = parser.parse_args()
    try:
        result = PeppolValidatorClient().validate(args.xml.read_bytes())
    except (OSError, ValidatorUnavailable) as exc:
        print(f"ONLINE_VALIDATOR_UNAVAILABLE: {exc}")
        return 2
    print(f"ONLINE_VALIDATOR_STATUS={result.status}")
    for error in result.errors: print(f"{error.severity}: {error.rule}: {error.message} ({error.location})")
    return 0 if result.status == "valid" else 1

if __name__ == "__main__": raise SystemExit(main())
