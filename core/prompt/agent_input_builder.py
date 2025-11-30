# core/prompt/agent_input_builder.py
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from core.config.run_config import RunItem


def build_agent_input(
    run_item: RunItem,
    profile_name: str,
    class_name: Optional[str],
    base_agent_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct the agent_input object passed into the model.

    This combines:
    - static runtime info (profile_name, class_name)
    - per-run agent_input overrides from the profile/run
    - the target_file path if present
    """
    agent_input_obj: Dict[str, Any] = {
        "profile_name": profile_name,
        "class_name": class_name or None,
    }

    if isinstance(base_agent_input, dict) and base_agent_input:
        agent_input_obj.update(base_agent_input)

    if run_item.target_file:
        agent_input_obj["target_file"] = run_item.target_file

    return agent_input_obj


def build_rules_block_for_run(run_item: RunItem) -> str:
    """Build a markdown-style rules block string for this run.

    - Uses per-run rules from runs.json (run_item.rules).
    - Adds a small set of global rules.
    - Deduplicates while preserving order.
    """
    base_rules: List[str] = [
        "Always respond strictly in the required JSON envelope.",
        "Never output markdown or prose outside the specified JSON format.",
    ]

    run_rules = run_item.rules or []

    combined: List[str] = []
    for r in base_rules + run_rules:
        if r not in combined:
            combined.append(r)

    return "\n".join(f"- {r}" for r in combined)


def inject_placeholders(
    run_params: Dict[str, Any],
    agent_input_obj: Dict[str, Any],
    rules_block: str,
    task_description: str,
    target_file: Optional[str],
    context_block: str,
) -> None:
    """Replace placeholder tokens in the OpenAI payload messages.

    Mutates `run_params` in-place. It expects the payload to have a `messages`
    list compatible with the OpenAI Chat Completions API.
    """
    agent_input_json = json.dumps(agent_input_obj, ensure_ascii=False, indent=2)

    for msg in run_params.get("messages", []):
        content = msg.get("content")
        if not isinstance(content, str):
            continue

        if "${agent_input}" in content:
            content = content.replace("${agent_input}", agent_input_json)

        if "${task_description}" in content:
            content = content.replace("${task_description}", task_description or "")

        if "${rules_block}" in content:
            content = content.replace("${rules_block}", rules_block)

        if "${target_file}" in content:
            content = content.replace("${target_file}", target_file or "")

        if "${context_block}" in content:
            content = content.replace("${context_block}", context_block or "")

        msg["content"] = content
