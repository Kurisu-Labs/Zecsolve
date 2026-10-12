"""replay-case: bounded local-file input; no packet-controlled executable paths."""

import argparse
import json
import os
from pathlib import Path

from zecsolve.adapters.verifier import VerifierAdapter
from zecsolve.replay.engine import replay_packet
from zecsolve.schemas.packet import MAX_PACKET_BYTES


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Replay a zecsolve packet offline without changing credit."
    )
    parser.add_argument("packet", type=Path, help="Local JSON packet file")
    parser.add_argument(
        "--verifier",
        type=Path,
        default=Path(os.environ.get("ZECSOLVE_VERIFIER_PATH", "target/debug/zecsolve-verifier")),
        help="Locally installed trusted verifier; never read from packet data",
    )
    args = parser.parse_args(argv)
    try:
        with args.packet.open("rb") as stream:
            data = stream.read(MAX_PACKET_BYTES + 1)
    except OSError:
        print(
            json.dumps(
                {
                    "schema_version": "case-replay-v1",
                    "status": "FAILED",
                    "code": "PACKET_READ_FAILED",
                }
            )
        )
        return 1
    result = replay_packet(data, VerifierAdapter(args.verifier))
    print(result.model_dump_json(indent=2))
    return {"REPRODUCED": 0, "LIMITED": 2, "UNSUPPORTED": 3, "FAILED": 1}[result.status]


if __name__ == "__main__":
    raise SystemExit(main())
