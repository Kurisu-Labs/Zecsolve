"""Verify a browser-downloaded packet through the real offline replay engine."""

import argparse
import os
from pathlib import Path

from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.replay.engine import replay_packet
from zecsolve.schemas.packet import MAX_PACKET_BYTES

if os.name == "nt":
    from windows_process import run_bounded
    from zecsolve.adapters import verifier

    verifier.run_bounded = run_bounded

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("packet", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
binary = (
    root / "target/debug" / ("zecsolve-verifier.exe" if os.name == "nt" else "zecsolve-verifier")
)
with args.packet.open("rb") as stream:
    data = stream.read(MAX_PACKET_BYTES + 1)
result = replay_packet(data, VerifierAdapter(binary))
print(result.model_dump_json())
raise SystemExit(1 if result.status == "FAILED" else 0)
