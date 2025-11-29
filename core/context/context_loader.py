# core/context/context_loader.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_context_params(project_root: Path, context_files: List[str]) -> Dict[str, Any]:
    """Load one or more context files and build a single OpenAI payload dict.

    Convention:
    - The FIRST file MUST be a JSON profile with a complete OpenAI payload:
        { "model": "...", "messages": [...], "temperature": ..., ... }
    - ALL remaining files (JSON or not) are treated as extra textual context.
      Their raw content is concatenated into a single 'context_block' string,
      which the profile can inject via a ${context_block} placeholder.

    The returned dict is the raw OpenAI request payload. A special meta key
    `_context_block` is optionally added and later consumed by the prompt
    rewriter.
    """
    if not context_files:
        raise ValueError("Run is missing 'context_file'. At least one path is required.")

    # 1) Load the profile JSON (first file)
    first = context_files[0]
    profile_path = (project_root / first).resolve()

    if not profile_path.exists():
        raise FileNotFoundError(f"context_file not found: {profile_path}")

    with profile_path.open("r", encoding="utf-8") as f:
        params = json.load(f)

    if not isinstance(params, dict):
        raise ValueError(f"context_file must contain a JSON object: {profile_path}")

    # 2) Load remaining files as raw text and aggregate
    text_blocks: List[str] = []

    for rel in context_files[1:]:
        path = (project_root / rel).resolve()
        if not path.exists():
            raise FileNotFoundError(f"extra context_file not found: {path}")

        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Non-text or non-UTF8 files are skipped for safety.
            continue

        header = f"=== CONTEXT FILE: {rel} ===\n"
        text_blocks.append(header + raw.strip() + "\n")

    if text_blocks:
        context_block = "\n\n".join(text_blocks)
        # Store as meta field; the prompt layer will inject via ${context_block}
        params["_context_block"] = context_block

    return params
