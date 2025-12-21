# core/strategy/rerun_strategy.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RerunAttempt:

    profile_file: str
    provider: Optional[str] = None
    context_files: List[str] = field(default_factory=list)
    target_file: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RerunAttempt":
        if not isinstance(data, dict):
            raise ValueError("RerunAttempt must be an object/dict.")

        profile_file = data.get("profile_file")
        if not isinstance(profile_file, str) or not profile_file.strip():
            raise ValueError("RerunAttempt.profile_file is required and must be a non-empty string.")

        provider = data.get("provider")
        if provider is not None and (not isinstance(provider, str) or not provider.strip()):
            raise ValueError("RerunAttempt.provider must be a non-empty string when provided.")

        context_files_raw = data.get("context_files", [])
        if not isinstance(context_files_raw, list) or not all(isinstance(x, str) for x in context_files_raw):
            raise ValueError("RerunAttempt.context_files must be a list of strings.")

        return RerunAttempt(
            profile_file=profile_file,
            provider=provider,
            context_files=list(context_files_raw),
        )


@dataclass(frozen=True)
class RerunBlock:
    name: Optional[str] = None
    method: Optional[str] = None
    attempts: List[RerunAttempt] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RerunBlock":
        if not isinstance(data, dict):
            raise ValueError("RerunBlock must be an object/dict.")

        name = data.get("name") or data.get("label")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("RerunBlock.name must be a non-empty string when provided.")

        method = data.get("method")
        if method is not None and (not isinstance(method, str) or not method.strip()):
            raise ValueError("RerunBlock.method must be a non-empty string when provided.")

        attempts_raw = data.get("attempts")
        if not isinstance(attempts_raw, list) or len(attempts_raw) == 0:
            raise ValueError("RerunBlock.attempts is required and must be a non-empty list.")

        attempts: List[RerunAttempt] = []
        for i, a in enumerate(attempts_raw):
            try:
                attempts.append(RerunAttempt.from_dict(a))
            except Exception as e:
                raise ValueError(f"Invalid RerunAttempt at attempts[{i}]: {e}") from e

        return RerunBlock(name=name, method=method, attempts=attempts)



@dataclass(frozen=True)
class RerunStrategy:

    blocks: List[RerunBlock] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any], *, require_unique_names: bool = True) -> "RerunStrategy":
        if not isinstance(data, dict):
            raise ValueError("RerunStrategy must be an object/dict.")

        blocks_raw = data.get("blocks", [])
        if not isinstance(blocks_raw, list):
            raise ValueError("RerunStrategy.blocks must be a list.")

        blocks: List[RerunBlock] = []
        for i, b in enumerate(blocks_raw):
            try:
                blocks.append(RerunBlock.from_dict(b))
            except Exception as e:
                raise ValueError(f"Invalid RerunBlock at blocks[{i}]: {e}") from e

        strategy = RerunStrategy(blocks=blocks)

        if require_unique_names:
            strategy._validate_unique_names()

        return strategy

    @staticmethod
    def load(path: str | Path, *, require_unique_names: bool = True) -> "RerunStrategy":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"rerun_strategy file not found: {p}")

        raw = p.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in rerun_strategy file: {p}. {e}") from e

        return RerunStrategy.from_dict(data, require_unique_names=require_unique_names)

    def get_block_by_name(self, name: str) -> Optional[RerunBlock]:
        if not isinstance(name, str) or not name.strip():
            return None

        for b in self.blocks:
            if b.name == name:
                return b
        return None

    def _validate_unique_names(self) -> None:
        seen: Dict[tuple[str, Optional[str]], int] = {}

        for idx, b in enumerate(self.blocks):
            if not b.name:
                continue

            key = (b.name, b.method)

            if key in seen:
                first = seen[key]
                raise ValueError(
                    f"Duplicate rerun block (name='{b.name}', method='{b.method}') "
                    f"in rerun_strategy.blocks (first at index {first}, duplicate at index {idx})."
                )

            seen[key] = idx


def get_block(self, name: str, method: Optional[str]) -> Optional[RerunBlock]:
    if not isinstance(name, str) or not name.strip():
        return None

    # If method is not provided, fall back to the first matching name (legacy behavior)
    if method is None or not isinstance(method, str) or not method.strip():
        return self.get_block_by_name(name)

    for b in self.blocks:
        if b.name == name and b.method == method:
            return b
    return None

