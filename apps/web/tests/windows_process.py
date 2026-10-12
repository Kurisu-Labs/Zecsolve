"""Windows-only pipe transport for the local browser harness, using the real binary.

The production adapter's selectors require POSIX pipes. Preserve its timeout,
stdout bound, discarded stderr and environment isolation during Windows testing.
"""

import subprocess
import threading

LIMIT = 32_768


def run_bounded(binary, args, cwd, timeout):
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
        overflow = threading.Event()

        def read():
            while chunk := process.stdout.read(4096):
                if len(output) + len(chunk) > LIMIT:
                    overflow.set()
                    process.kill()
                    return
                output.extend(chunk)

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            process.wait(timeout=timeout)
            reader.join(timeout=timeout)
            if overflow.is_set():
                raise OverflowError
            if reader.is_alive():
                raise TimeoutError
            if process.returncode:
                raise subprocess.SubprocessError("Verifier exited unsuccessfully")
            return bytes(output)
        except subprocess.TimeoutExpired as error:
            raise TimeoutError from error
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            reader.join(timeout=1)
