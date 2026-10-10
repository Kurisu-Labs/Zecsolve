import os
import selectors
import subprocess
import time
from pathlib import Path

MAX_OUTPUT_BYTES = 32_768


def run_bounded(binary: Path, args: list[str], cwd: Path, timeout: float) -> bytes:
    # Only bounded JSON stdout is retained. Untrusted stderr is neither returned nor logged.
    with subprocess.Popen(
        [str(binary), *args],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=cwd,
        env={"LANG": "C.UTF-8"},
    ) as process:
        output = bytearray()
        deadline = time.monotonic() + timeout
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
