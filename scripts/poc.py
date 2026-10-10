"""Offline integration demonstration; does not write an allocation or claim chain inclusion."""

import json
from dataclasses import asdict
from pathlib import Path

from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.config import Settings
from zecsolve.domain.rules import InvoiceTerms, evaluate

root = Path(__file__).resolve().parents[1]
settings = Settings()
adapter = VerifierAdapter(settings.verifier_path, settings.verifier_timeout_seconds)
raw_tx = (root / "fixtures/mainnet/transaction.hex").read_text()
valid = adapter.verify((root / "fixtures/mainnet/receipt.json").read_text(), raw_tx)
invalid = adapter.verify((root / "fixtures/negative/tampered-ock.json").read_text(), raw_tx)
if valid.receipt_state != "VALID" or invalid.receipt_state != "INVALID":
    raise SystemExit(f"POC failed: valid={valid.reason_code}, tampered={invalid.reason_code}")
output = valid.output
terms = InvoiceTerms(
    invoice_id="synthetic-demo-invoice",
    expected_zat=200_000,
    network="mainnet",
    pool="orchard",
    receiver_hex="ab7196fa80c61c65508be3923dbb8b416fc9fc50516e33e7be761e5da01b35a857f1770483a36b0f2b07ad",
    expected_memo_hex=b"glasspane first receipt".ljust(512, b"\0").hex(),
)
print(
    json.dumps(
        {
            "app": "zecsolve",
            "mode": "historical fixture with synthetic invoice; no live confirmation or allocation",
            "valid_receipt": {"state": valid.receipt_state, "amount_zat": output.amount_zat},
            "tampered_receipt": {"state": invalid.receipt_state, "reason": invalid.reason_code},
            "chain_state": valid.chain_state,
            "evaluation": asdict(evaluate(terms, valid)),
        },
        indent=2,
    )
)
