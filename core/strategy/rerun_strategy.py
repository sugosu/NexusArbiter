# core/strategy/rerun_strategy.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ----------------------------------------------------------------------
# Single rerun attempt (profile override, provider override, context)
# ----------------------------------------------------------------------
@dataclass
class RerunAttempt:
    profile_file: Optional[str] = None
    provider: Optional[str] = None
    context_files: Optional[List[str]] = None


# ----------------------------------------------------------------------
# A block of attempts (example: 3 possible retries)
# ----------------------------------------------------------------------
@dataclass
class RerunBlock:
    attempts: List[RerunAttempt] = field(default_factory=list)
    current_attempt: int = 0  # increments each time a validator requests rerun

    @staticmethod
    def from_dict(data: dict) -> "RerunBlock":
        attempts = [
            RerunAttempt(
                profile_file=a.get("profile_file"),
                provider=a.get("provider"),
                context_files=a.get("context_files"),
            )
            for a in data.get("attempts", [])
        ]
        return RerunBlock(attempts=attempts)


# ----------------------------------------------------------------------
# Whole strategy file (.json)
# Supports multiple blocks; validator selects rerun_index = which block.
# ----------------------------------------------------------------------
@dataclass
class RerunStrategy:
    blocks: List[RerunBlock]

    @staticmethod
    def from_file(path: Path | str) -> "RerunStrategy":
        if isinstance(path, str):
            path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        # Accept both new field "blocks" and backward-compatible "strategy"
        data_blocks = raw.get("blocks")
        if data_blocks is None:
            data_blocks = raw.get("strategy")  # backward compatibility

        if not isinstance(data_blocks, list):
            raise ValueError("rerun_strategy.json must contain a 'blocks' list.")

        blocks = [RerunBlock.from_dict(b) for b in data_blocks]
        return RerunStrategy(blocks=blocks)

# core/strategy/rerun_strategy.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ----------------------------------------------------------------------
# Single rerun attempt (profile override, provider override, context)
# ----------------------------------------------------------------------
@dataclass
class RerunAttempt:
    profile_file: Optional[str] = None
    provider: Optional[str] = None
    context_files: Optional[List[str]] = None


# ----------------------------------------------------------------------
# A block of attempts (example: 3 possible retries)
# ----------------------------------------------------------------------
@dataclass
class RerunBlock:
    attempts: List[RerunAttempt] = field(default_factory=list)
    current_attempt: int = 0  # increments each time a validator requests rerun

    @staticmethod
    def from_dict(data: dict) -> "RerunBlock":
        attempts = [
            RerunAttempt(
                profile_file=a.get("profile_file"),
                provider=a.get("provider"),
                context_files=a.get("context_files"),
            )
            for a in data.get("attempts", [])
        ]
        return RerunBlock(attempts=attempts)


# ----------------------------------------------------------------------
# Whole strategy file (.json)
# Supports multiple blocks; validator selects rerun_index = which block.
# ----------------------------------------------------------------------
    @staticmethod
    def from_file_for_target(path: Path | str, target_run: str) -> "RerunStrategy":
        """
        Load a rerun strategy for a specific target_run.

        Supports two JSON shapes:

        1) Legacy / simple:
           {
             "blocks": [ { "attempts": [ ... ] } ]
           }

        2) Index form (list of entries):
           [
             {
               "target_run": "SomeRunName",
               "blocks": [ { "attempts": [ ... ] } ],
               "description": "optional"
             },
             {
               "target_run": "AnotherRun",
               "blocks": [ ... ]
             }
           ]
        """
        if isinstance(path, str):
            path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        # Case 1: legacy / simple format (dict with "blocks"/"strategy")
        if isinstance(raw, dict):
            data_blocks = raw.get("blocks")
            if data_blocks is None:
                data_blocks = raw.get("strategy")  # backward compatibility

            if not isinstance(data_blocks, list):
                raise ValueError(
                    "rerun_strategy.json must contain a 'blocks' list."
                )

            blocks = [RerunBlock.from_dict(b) for b in data_blocks]
            return RerunStrategy(blocks=blocks)

        # Case 2: index format (list of entries, each with target_run + blocks)
        if isinstance(raw, list):
            entry = None
            for item in raw:
                if not isinstance(item, dict):
                    continue
                if item.get("target_run") == target_run:
                    entry = item
                    break

            if entry is None:
                raise ValueError(
                    f"Rerun strategy index has no entry for target_run={target_run!r}"
                )

            data_blocks = entry.get("blocks")
            if data_blocks is None:
                data_blocks = entry.get("strategy")

            if not isinstance(data_blocks, list):
                raise ValueError(
                    "Rerun strategy index entry must contain a 'blocks' list."
                )

            blocks = [RerunBlock.from_dict(b) for b in data_blocks]
            return RerunStrategy(blocks=blocks)

        raise ValueError("Unsupported rerun strategy file format")
