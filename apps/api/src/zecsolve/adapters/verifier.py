import hashlib
import os
import selectors
import subprocess
import tempfile
import time
from pathlib import Path

from pydantic import ValidationError

from zecsolve.domain.statuses import ReceiptState
from zecsolve.schemas.verification import VerificationReport

MAX_RECEIPT_BYTES = 16_384
MAX_TX_HEX_BYTES = 4_000_002
MAX_OUTPUT_BYTES = 32_768


class VerifierAdapter:
    def __init__(self, binary: Path, timeout: float = 10):
        self.binary = binary.resolve()
        self.timeout = timeout

    def available(self) -> bool:
        return self.binary.is_file() and os.access(self.binary, os.X_OK)

    def verify(self, receipt: str | None, raw_tx_hex: str | None) -> VerificationReport:
        def result(state: ReceiptState, code: str) -> VerificationReport:
            return VerificationReport(
                receipt_state=state,
                reason_code=code,
                receipt_sha256=(hashlib.sha256(receipt.encode()).hexdigest() if receipt else None),
            )

        if not receipt:
            return result(ReceiptState.NONE, "RECEIPT_MISSING")
        if not raw_tx_hex:
            return result(ReceiptState.UNAVAILABLE, "RAW_TRANSACTION_UNAVAILABLE")
        if len(receipt.encode()) > MAX_RECEIPT_BYTES or len(raw_tx_hex.encode()) > MAX_TX_HEX_BYTES:
            return result(ReceiptState.ERROR, "INPUT_TOO_LARGE")
        if not self.available():
            return result(ReceiptState.UNAVAILABLE, "VERIFIER_UNAVAILABLE")
        with tempfile.TemporaryDirectory(prefix="zecsolve-") as directory:
            receipt_file = Path(directory, "receipt.json")
            tx_file = Path(directory, "transaction.hex")
            receipt_file.write_text(receipt, encoding="utf-8")
            tx_file.write_text(raw_tx_hex, encoding="utf-8")
            try:
                stdout = self._run(receipt_file, tx_file)
            except TimeoutError:
                return result(ReceiptState.ERROR, "VERIFIER_TIMEOUT")
            except OverflowError:
                return result(ReceiptState.ERROR, "VERIFIER_OUTPUT_TOO_LARGE")
            except (OSError, subprocess.SubprocessError):
                return result(ReceiptState.ERROR, "VERIFIER_PROCESS_ERROR")
            try:
                report = VerificationReport.model_validate_json(stdout)
            except (ValueError, ValidationError):
                return result(ReceiptState.ERROR, "VERIFIER_PROTOCOL_ERROR")
            if report.receipt_state == ReceiptState.VALID:
                try:
                    tx_hash = hashlib.sha256(bytes.fromhex(raw_tx_hex.strip())).hexdigest()
                except ValueError:
                    return result(ReceiptState.ERROR, "VERIFIER_PROTOCOL_ERROR")
                if (
                    report.receipt_sha256 != hashlib.sha256(receipt.encode()).hexdigest()
                    or report.raw_tx_sha256 != tx_hash
                ):
                    return result(ReceiptState.ERROR, "VERIFIER_PROTOCOL_ERROR")
            return report

    def _run(self, receipt_file: Path, tx_file: Path) -> bytes:
        # Only bounded JSON stdout is retained. Untrusted stderr is neither returned nor logged.
        with subprocess.Popen(
            [str(self.binary), "--receipt", str(receipt_file), "--raw-tx", str(tx_file)],
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=receipt_file.parent,
            env={"LANG": "C.UTF-8"},
        ) as process:
            output = bytearray()
            deadline = time.monotonic() + self.timeout
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError
                        for key, _ in selector.select(remaining):
                            chunk = os.read(key.fileobj.fileno(), 4096)
                            if not chunk:
                                selector.unregister(key.fileobj)
                            else:
                                output.extend(chunk)
                                if len(output) > MAX_OUTPUT_BYTES:
                                    raise OverflowError
                try:
                    returncode = process.wait(timeout=max(0.001, deadline - time.monotonic()))
                except subprocess.TimeoutExpired as error:
                    raise TimeoutError from error
                if returncode != 0:
                    raise subprocess.SubprocessError("Verifier exited unsuccessfully")
                return bytes(output)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
