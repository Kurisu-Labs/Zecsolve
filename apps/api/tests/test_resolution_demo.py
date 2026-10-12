import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.postgres


def test_isolated_demo_uses_real_recovery_and_labels_simulated_credit(root):
    if not os.getenv("ZECSOLVE_TEST_DATABASE_URL"):
        pytest.skip("Disposable PostgreSQL required")
    result = subprocess.run(
        [sys.executable, str(root / "scripts/demo_resolution.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    trace = json.loads(result.stdout)
    assert trace["source_kind"] == "SIMULATED" and trace["live_confirmation"] is False
    assert trace["offline_approval"] == "CREDIT_INELIGIBLE"
    assert trace["receipt_state"] == "VALID" and trace["recovered_zat"] == 100_000
    assert trace["balances"] == {
        "credited_zat": 100_000,
        "outstanding_zat": 100_000,
        "candidate_zat": 0,
    }
    assert trace["retry_same_resolution"] is True
    assert trace["second_invoice"] == "OUTPUT_ALLOCATION_CONFLICT"
    assert (
        trace["tampered_receipt"] == "INVALID" and trace["tampered_approval"] == "CREDIT_INELIGIBLE"
    )
    assert trace["schema_removed"] is True
    assert trace["rejected_invoice_credited_zat"] == 0
    assert trace["tampered_reason"] == "OUTPUT_RECOVERY_FAILED"
