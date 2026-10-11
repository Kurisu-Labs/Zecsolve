"""Regenerate the machine-readable Rust/Python boundary from its validation model."""

import json
from pathlib import Path

from zecsolve.schemas.address import AddressNormalizationReport, NormalizeAddressRequest
from zecsolve.schemas.invoice import InvoiceCreateRequest, InvoiceSnapshotV1
from zecsolve.schemas.verification import VerificationReport

root = Path(__file__).resolve().parents[1]
for name, model in (
    ("verifier-result", VerificationReport),
    ("normalize-address-request", NormalizeAddressRequest),
    ("normalize-address-result", AddressNormalizationReport),
    ("invoice-create-request", InvoiceCreateRequest),
    ("invoice-snapshot", InvoiceSnapshotV1),
):
    target = root / f"contracts/{name}.schema.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
