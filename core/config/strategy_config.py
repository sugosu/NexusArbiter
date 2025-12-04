from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
import json


# ---------------------------------------------------------------------------
# Attempt-level override
# ---------------------------------------------------------------------------

@dataclass
class StrategyAttempt:
    """
    A single retry attempt override.
    All fields are optional — engine falls back to the original RunItem.
    """

    profile: Optional[str] = None
    provider: Optional[str] = None
    retry_context_files: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# A single block containing multiple attempts
# ---------------------------------------------------------------------------

@dataclass
class StrategyBlock:
    label: Optional[str]
    attempts: List[StrategyAttempt]


# ---------------------------------------------------------------------------
# The entire strategy file (list of blocks)
# ---------------------------------------------------------------------------

@dataclass
class StrategyFile:
    blocks: List[StrategyBlock]

    @staticmethod
    def from_file(path: Path | str) -> "StrategyFile":
        """
        Load a strategy JSON file.

        Example schema:
        {
          "blocks": [
            {
              "label": "first_codegen_block",
              "attempts": [
                { "profile": "abc.json", "provider": "openai", "retry_context_files": [...] },
                { ... }
              ]
            },
            ...
          ]
        }
        """
        if isinstance(path, str):
            path = Path(path)

        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        blocks_raw = raw.get("blocks", [])
        blocks_parsed: List[StrategyBlock] = []

        for block in blocks_raw:
            label = block.get("label")
            attempts_raw = block.get("attempts", [])

            attempts: List[StrategyAttempt] = []
            for att in attempts_raw:
                attempts.append(
                    StrategyAttempt(
                        profile=att.get("profile"),
                        provider=att.get("provider"),
                        retry_context_files=att.get("retry_context_files"),
                    )
                )

            blocks_parsed.append(
                StrategyBlock(label=label, attempts=attempts)
            )

        return StrategyFile(blocks=blocks_parsed)

    def get_attempt(self, block_index: int, attempt_index: int) -> Optional[StrategyAttempt]:
        """
        Safely fetch one attempt. Returns None if:
        - invalid block
        - invalid attempt index
        """
        if block_index < 0 or block_index >= len(self.blocks):
            return None

        block = self.blocks[block_index]

        if attempt_index < 0 or attempt_index >= len(block.attempts):
            return None

        return block.attempts[attempt_index]
