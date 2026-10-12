"""Run the installed replay CLI inside a disposable, network-disabled container."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    data = sys.stdin.buffer.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise ValueError("Rehearsal packet exceeds limit")
    # Only tmpfs receives packet bytes; no credentials or database are mounted.
    with tempfile.TemporaryDirectory() as directory:
        packet = Path(directory) / "packet.json"
        packet.write_bytes(data)
        result = subprocess.run(
            ["replay-case", str(packet), "--verifier", "/usr/local/bin/zecsolve-verifier"],
            capture_output=True,
            timeout=60,
            check=False,
        )
    if result.returncode not in (0, 1, 2, 3):
        raise RuntimeError("Replay CLI failed unexpectedly")
    print(json.dumps({"exit_code": result.returncode, "result": json.loads(result.stdout)}))


if __name__ == "__main__":
    main()
