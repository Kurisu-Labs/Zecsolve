import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

from zecsolve.adapters.process import run_bounded
from zecsolve.schemas.address import (
    MAX_ADDRESS_REQUEST_BYTES,
    AddressNormalizationReport,
    NormalizeAddressRequest,
)


class AddressNormalizer:
    def __init__(self, binary: Path, timeout: float = 10):
        self.binary = binary.resolve()
        self.timeout = timeout

    def normalize(self, request: NormalizeAddressRequest) -> AddressNormalizationReport:
        payload = request.model_dump_json().encode("utf-8")
        input_hash = hashlib.sha256(payload).hexdigest()

        def failure(state, code):
            return AddressNormalizationReport(
                state=state, reason_code=code, input_sha256=input_hash
            )

        if len(payload) > MAX_ADDRESS_REQUEST_BYTES:
            return failure("ERROR", "INPUT_TOO_LARGE")
        if not self.binary.is_file() or not os.access(self.binary, os.X_OK):
            return failure("UNAVAILABLE", "NORMALIZER_UNAVAILABLE")
        try:
            with tempfile.TemporaryDirectory(prefix="zecsolve-address-") as directory:
                path = Path(directory, "request.json")
                path.write_bytes(payload)
                stdout = run_bounded(
                    self.binary,
                    ["normalize-address", "--input", str(path)],
                    path.parent,
                    self.timeout,
                )
        except TimeoutError:
            return failure("ERROR", "NORMALIZER_TIMEOUT")
        except OverflowError:
            return failure("ERROR", "NORMALIZER_OUTPUT_TOO_LARGE")
        except (OSError, subprocess.SubprocessError):
            return failure("ERROR", "NORMALIZER_PROCESS_ERROR")
        try:
            report = AddressNormalizationReport.model_validate_json(stdout)
        except ValueError:
            return failure("ERROR", "NORMALIZER_PROTOCOL_ERROR")
        if "schema_version" not in report.model_fields_set or report.input_sha256 != input_hash:
            return failure("ERROR", "NORMALIZER_PROTOCOL_ERROR")
        if report.receiver and (
            report.receiver.network != request.network or report.receiver.pool != request.pool
        ):
            return failure("ERROR", "NORMALIZER_PROTOCOL_ERROR")
        return report
