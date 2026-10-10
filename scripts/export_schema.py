"""Regenerate the machine-readable Rust/Python boundary from its validation model."""

import json
from pathlib import Path

from zecsolve.schemas.verification import VerificationReport

root = Path(__file__).resolve().parents[1]
target = root / "contracts/verifier-result.schema.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(VerificationReport.model_json_schema(), indent=2) + "\n")
