import json
import subprocess

import pytest


def executable(tmp_path, program):
    binary = tmp_path / "process-test"
    binary.write_text("#!/usr/bin/python3\n" + program + "\n")
    binary.chmod(0o700)
    return binary


def test_bounded_process_isolates_environment_stdin_and_working_directory(tmp_path, monkeypatch):
    from zecsolve.adapters.process import run_bounded

    monkeypatch.setenv("ZECSOLVE_POC_TOKEN", "must-not-inherit")
    binary = executable(
        tmp_path,
        "import os,sys,json; print(json.dumps([os.getenv('ZECSOLVE_POC_TOKEN'), "
        "os.getcwd(), sys.stdin.read(), sys.argv[1:]]))",
    )
    result = run_bounded(binary, ["literal; not a shell"], tmp_path, 2)
    assert json.loads(result) == [None, str(tmp_path), "", ["literal; not a shell"]]


@pytest.mark.parametrize(
    ("program", "error"),
    [
        ("import time; time.sleep(5)", TimeoutError),
        ("import os; os.write(1, b'x' * 40000)", OverflowError),
        ("raise SystemExit(1)", subprocess.SubprocessError),
        ("import os,time; os.close(1); time.sleep(5)", TimeoutError),
    ],
)
def test_bounded_process_enforces_limits_and_exit_status(tmp_path, program, error):
    from zecsolve.adapters.process import run_bounded

    with pytest.raises(error):
        run_bounded(executable(tmp_path, program), [], tmp_path, 0.2)
