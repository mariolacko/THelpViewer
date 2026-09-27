"""Attach a browser terminal to commands deliberately launched on the server CLI.

No HTTP endpoint starts a process.  A random per-job key protects both output
and input, and the input queue stops accepting writes after the process exits.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
import pty
import re
import secrets
import select
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from .config import load_config


JOB_ID = re.compile(r"^[A-Za-z0-9_-]{12}$")
MAX_CHUNK = 65536


def _write_status(job_dir: Path, status: dict[str, object]) -> None:
    temporary = job_dir / "status.tmp"
    temporary.write_text(json.dumps(status), encoding="utf-8")
    temporary.replace(job_dir / "status.json")


def authorize_job(state_dir: Path, job_id: str, key: str) -> tuple[Path, dict[str, object]]:
    if not JOB_ID.fullmatch(job_id) or not key:
        raise HTTPException(status_code=404, detail="Terminal job not found")
    job_dir = state_dir / "terminal" / job_id
    try:
        status = json.loads((job_dir / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="Terminal job not found") from None
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if not secrets.compare_digest(digest, str(status.get("key_hash", ""))):
        raise HTTPException(status_code=404, detail="Terminal job not found")
    return job_dir, status


def read_job(state_dir: Path, job_id: str, key: str, offset: int = 0) -> dict[str, object]:
    job_dir, status = authorize_job(state_dir, job_id, key)
    log_path = job_dir / "output.log"
    with log_path.open("rb") as log:
        log.seek(min(max(0, offset), log.seek(0, os.SEEK_END)))
        start = log.tell()
        output = log.read(MAX_CHUNK)
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    text = decoder.decode(output, final=not status.get("running"))
    pending = decoder.getstate()[0]
    return {
        "label": status.get("label", "Command"),
        "running": status.get("running", False),
        "exit_code": status.get("exit_code"),
        "output": text,
        "offset": start + len(output) - len(pending),
    }


def send_input(state_dir: Path, job_id: str, key: str, value: str) -> None:
    job_dir, status = authorize_job(state_dir, job_id, key)
    if not status.get("running"):
        raise HTTPException(status_code=409, detail="Terminal job has finished")
    if not value or len(value.encode("utf-8")) > 2048 or "\x00" in value or "\n" in value or "\r" in value:
        raise HTTPException(status_code=422, detail="Enter one non-empty line (at most 2048 bytes)")
    encoded = (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
    descriptor = os.open(job_dir / "input.queue", os.O_WRONLY | os.O_APPEND)
    try:
        os.write(descriptor, encoded)
    finally:
        os.close(descriptor)


def run_command(state_dir: Path, command: list[str], label: str = "Command") -> int:
    if not command:
        raise ValueError("A server command is required")
    terminal_dir = state_dir / "terminal"
    terminal_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    job_id = secrets.token_urlsafe(9)
    key = secrets.token_urlsafe(24)
    job_dir = terminal_dir / job_id
    job_dir.mkdir(mode=0o700)
    (job_dir / "input.queue").touch(mode=0o600)
    (job_dir / "output.log").touch(mode=0o600)
    status: dict[str, object] = {
        "label": label[:80],
        "key_hash": hashlib.sha256(key.encode("utf-8")).hexdigest(),
        "running": True,
        "exit_code": None,
        "started": datetime.now(timezone.utc).isoformat(),
    }
    _write_status(job_dir, status)
    print(f"Terminal job ID: {job_id}\nTerminal access key: {key}", flush=True)

    master, slave = pty.openpty()
    process = None
    try:
        try:
            process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        except OSError as error:
            message = f"Could not start command: {error}\n"
            (job_dir / "output.log").write_text(message, encoding="utf-8")
            print(message, file=sys.stderr, end="")
            return 127
        os.close(slave)
        slave = -1
        pending = b""
        queue_offset = 0
        with (job_dir / "output.log").open("ab", buffering=0) as log:
            while True:
                with (job_dir / "input.queue").open("rb") as queue:
                    queue.seek(queue_offset)
                    pending += queue.read()
                    queue_offset = queue.tell()
                while b"\n" in pending:
                    entry, pending = pending.split(b"\n", 1)
                    try:
                        os.write(master, (json.loads(entry) + "\n").encode("utf-8"))
                    except (OSError, ValueError, TypeError):
                        pass
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try:
                        output = os.read(master, 8192)
                    except OSError:
                        output = b""
                    if output:
                        log.write(output)
                        sys.stdout.buffer.write(output)
                        sys.stdout.buffer.flush()
                    else:
                        break
                elif process.poll() is not None:
                    break
        return process.wait()
    except KeyboardInterrupt:
        if process is not None:
            process.terminate()
            return process.wait()
        return 130
    finally:
        if slave >= 0:
            os.close(slave)
        os.close(master)
        status["running"] = False
        status["exit_code"] = process.returncode if process is not None else 127
        status["finished"] = datetime.now(timezone.utc).isoformat()
        _write_status(job_dir, status)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a server command and attach it to THelpViewer")
    parser.add_argument("--label", default="Command", help="Short title displayed in the viewer")
    parser.add_argument("--state-dir", type=Path, default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("specify a command after --")
    return run_command(args.state_dir or load_config().state_dir, command, args.label)


if __name__ == "__main__":
    raise SystemExit(main())
