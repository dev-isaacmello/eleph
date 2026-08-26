"""An append-only log on disk, which is the whole of what the program knows.

Nothing here is a checkpoint or a snapshot. Restarting reads the events back
in order and everything else -- the index, the ledger, every answer the program
would give -- falls out of them again. That is the same claim the language
makes about memory, held to at the level of the process: a program that has
been restarted is not a program that has forgotten.

A line is one event, JSON, newline-terminated. A crash mid-write leaves a
partial final line, which `load` detects and drops: an event that was never
finished being written is an event that did not happen.
"""

import json
import os
import pathlib
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple


class CorruptLog(Exception):
    pass


@dataclass
class Store:
    path: pathlib.Path
    fsync: bool = False          # durability per event, at roughly 100x cost
    _handle: Optional[object] = None
    truncated: int = 0           # bytes dropped from an interrupted write

    def __post_init__(self):
        self.path = pathlib.Path(self.path)

    # ------------------------------------------------------------- reading
    def load(self) -> Iterator[Tuple[str, tuple]]:
        """Replay the history. A torn final line is dropped, not guessed at."""
        if not self.path.exists():
            return
        good_bytes = 0
        with open(self.path, "rb") as f:
            raw = f.read()
        for line in raw.split(b"\n"):
            if not line:
                continue
            if not line.endswith(b"}"):
                self.truncated = len(raw) - good_bytes
                break
            try:
                rec = json.loads(line)
                name, args = rec["e"], tuple(rec["a"])
            except (ValueError, KeyError, TypeError):
                self.truncated = len(raw) - good_bytes
                break
            good_bytes += len(line) + 1
            yield name, args
        if self.truncated:
            self._repair(good_bytes)

    def _repair(self, good_bytes: int):
        """Cut the unfinished tail so the next append lands on a clean edge."""
        with open(self.path, "r+b") as f:
            f.truncate(good_bytes)

    # ------------------------------------------------------------- writing
    def open(self):
        if self._handle is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = open(self.path, "a", buffering=1)
        return self._handle

    def append(self, name: str, args: tuple):
        h = self.open()
        h.write(json.dumps({"e": name, "a": list(args)},
                           ensure_ascii=False, separators=(",", ":")) + "\n")
        if self.fsync:
            h.flush()
            os.fsync(h.fileno())

    def close(self):
        if self._handle is not None:
            self._handle.flush()
            os.fsync(self._handle.fileno())
            self._handle.close()
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
