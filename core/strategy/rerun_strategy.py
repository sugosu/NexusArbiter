# core/strategy/rerun_strategy.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union, Any, Dict


@dataclass
class RerunAttempt:
    profile_file: Optional[str] = None
    provider: Optional[str] = None
    context_files: Optional[List[str]] = None


@dataclass
class RerunBlock:
    attempts: List[RerunAttempt] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RerunBlock":
        attempts_raw = data.get("attempts", [])
        if attempts_raw is None:
            attempts_raw = []
        if not isinstance(attempts_raw, list):
            raise ValueError("rerun strategy block 'attempts' must be a list.")

        attempts: List[RerunAttempt] = []
        for a in attempts_raw:
            if not isinstance(a, dict):
                raise ValueError("rerun strategy attempt must be an object.")
            attempts.append(
                RerunAttempt(
                    profile_file=a.get("profile_file"),
                    provider=a.get("provider"),
                    context_files=a.get("context_files"),
                )
            )
        return RerunBlock(attempts=attempts)


@dataclass
class RerunStrategy:
    blocks: List[RerunBlock]

    @staticmethod
    def _parse_blocks(raw: Dict[str, Any]) -> List[RerunBlock]:
        data_blocks = raw.get("blocks")
        if data_blocks is None:
            data_blocks = raw.get("strategy")  # backward compatibility

        if not isinstance(data_blocks, list):
            raise ValueError("rerun_strategy.json must contain a 'blocks' list.")

        return [RerunBlock.from_dict(b) for b in data_blocks]

    @staticmethod
    def from_file(path: Path | str) -> "RerunStrategy":
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, dict):
            raise ValueError("rerun strategy file must be an object with 'blocks'.")

        return RerunStrategy(blocks=RerunStrategy._parse_blocks(raw))

    @staticmethod
    def from_file_for_target(path: Path | str, target_run: str) -> "RerunStrategy":
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        # Case 1: legacy / simple format (dict)
        if isinstance(raw, dict):
            return RerunStrategy(blocks=RerunStrategy._parse_blocks(raw))

        # Case 2: index format (list of entries)
        if isinstance(raw, list):
            entry = next(
                (x for x in raw if isinstance(x, dict) and x.get("target_run") == target_run),
                None,
            )
            if entry is None:
                raise ValueError(f"Rerun strategy index has no entry for target_run={target_run!r}")

            return RerunStrategy(blocks=RerunStrategy._parse_blocks(entry))

        raise ValueError("Unsupported rerun strategy file format.")
