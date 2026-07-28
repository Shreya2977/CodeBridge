"""
sandbox.py
----------
Manages a single long-lived Docker container and runs code inside it via
`docker exec`, rather than spinning up a fresh container per test case
(much faster, still isolated).

Requires: docker python SDK  ->  pip install docker
Requires: the image built from docker/Dockerfile, tagged `codetranslate-sandbox`

    docker build -t codetranslate-sandbox -f docker/Dockerfile docker/
"""

import io
import os
import tarfile
import uuid
import docker
from dataclasses import dataclass


@dataclass
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False


class Sandbox:
    IMAGE = "codetranslate-sandbox"
    WORKDIR = "/home/sandboxuser"

    def __init__(self, mem_limit="256m", nano_cpus=1_000_000_000, timeout=10):
        """
        mem_limit: container memory cap
        nano_cpus: 1e9 = 1 CPU core
        timeout: seconds allowed per single run before we kill it
        """
        self.client = docker.from_env()
        self.timeout = timeout
        self.container = self.client.containers.run(
            self.IMAGE,
            detach=True,
            mem_limit=mem_limit,
            nano_cpus=nano_cpus,
            network_mode="none",       # no internet access from inside sandbox
            security_opt=["no-new-privileges"],
            pids_limit=64,             # stop fork bombs
        )

    def _put_file(self, filename: str, content: str):
        """Write a file into the running container without touching the host disk."""
        data = content.encode("utf-8")
        tarstream = io.BytesIO()
        with tarfile.open(fileobj=tarstream, mode="w") as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        tarstream.seek(0)
        self.container.put_archive(self.WORKDIR, tarstream)

    def _exec(self, cmd: str) -> RunResult:
        try:
            result = self.container.exec_run(
                cmd=["bash", "-c", f"timeout {self.timeout} {cmd}"],
                workdir=self.WORKDIR,
                demux=True,
            )
            stdout, stderr = result.output
            stdout = (stdout or b"").decode("utf-8", errors="replace")
            stderr = (stderr or b"").decode("utf-8", errors="replace")
            timed_out = result.exit_code == 124  # `timeout` command's exit code
            return RunResult(stdout, stderr, result.exit_code, timed_out)
        except Exception as e:
            return RunResult("", str(e), -1)

    def run_fortran(self, source_code: str, stdin_input: str = "") -> RunResult:
        run_id = uuid.uuid4().hex[:8]
        src_name = f"prog_{run_id}.f90"
        bin_name = f"prog_{run_id}"
        self._put_file(src_name, source_code)

        compile_result = self._exec(f"gfortran -O0 -o {bin_name} {src_name}")
        if compile_result.exit_code != 0:
            return RunResult("", f"COMPILE ERROR:\n{compile_result.stderr}", compile_result.exit_code)

        if stdin_input:
            self._put_file(f"{run_id}.stdin", stdin_input)
            return self._exec(f"./{bin_name} < {run_id}.stdin")
        return self._exec(f"./{bin_name}")

    def run_python(self, source_code: str, stdin_input: str = "") -> RunResult:
        run_id = uuid.uuid4().hex[:8]
        src_name = f"prog_{run_id}.py"
        self._put_file(src_name, source_code)

        if stdin_input:
            self._put_file(f"{run_id}.stdin", stdin_input)
            return self._exec(f"python3 {src_name} < {run_id}.stdin")
        return self._exec(f"python3 {src_name}")

    def close(self):
        try:
            self.container.remove(force=True)
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


if __name__ == "__main__":
    # quick smoke test
    with Sandbox() as sb:
        fortran_hello = """
        program hello
            print *, "hello from fortran"
        end program hello
        """
        print(sb.run_fortran(fortran_hello))

        python_hello = 'print("hello from python")'
        print(sb.run_python(python_hello))
