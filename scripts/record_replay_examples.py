"""Record real CLI outcomes for deterministic public/synthetic packet variants."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from zecsolve.domain.snapshots import digest

root = Path(__file__).resolve().parents[1]
original = (root / "fixtures/packets/complete-v1.json").read_bytes()
variants = {
    "valid": original,
    "tampered": original.replace(b"Synthetic demonstration only", b"Synthetic demonstration onl!"),
    "scoped": (root / "fixtures/packets/scoped.json").read_bytes(),
}
for name, version in [("missing-version", None), ("unsupported-version", "999.0.0")]:
    raw = json.loads(original)
    raw["payload"]["implementations"]["verifiers"][0]["version"] = version
    raw["integrity"]["payload_sha256"] = digest(raw["payload"])
    variants[name] = json.dumps(raw).encode()
results = {}
with tempfile.TemporaryDirectory(prefix="zecsolve-public-replay-") as directory:
    for name, data in variants.items():
        source = Path(directory) / f"{name}.json"
        source.write_bytes(data)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "zecsolve.replay",
                str(source),
                "--verifier",
                str(root / "target/debug/zecsolve-verifier"),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        results[name] = {"exit_code": result.returncode, "output": json.loads(result.stdout)}
(root / "fixtures/packets/replay-results.json").write_text(json.dumps(results, indent=2) + "\n")
