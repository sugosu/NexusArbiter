# app/app.py
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.logger import BasicLogger
from core.ai_client.ai_client import OpenAIClient
from core.ai_client.ai_response_parser import AIResponseParser

from core.files.class_generator import ClassGenerator
from core.files.class_reader import PythonFileReader

from core.git.repo_config import RepoConfig
from core.git.git_client import GitClient
from core.git.git_manager import GitManager
from core.config.run_config import RunItem  # optional, only if you want type hints

def build_rules_block_for_run(run_item: RunItem) -> str:
    """
    Build the rules block string for this run.

    - Uses only per-run rules from runs.json (run_item.rules).
    - Optionally you can define a few global rules in base_rules.
    - Deduplicates while preserving order.
    """
    # Optional global rules you want every call to obey.
    base_rules: List[str] = [
        # Example (you can remove or edit these):
        "Always respond strictly in the required JSON envelope.",
        "Never output markdown or prose outside the specified JSON format.",
    ]

    run_rules = run_item.rules or []

    combined: List[str] = []
    for r in base_rules + run_rules:
        if r not in combined:
            combined.append(r)

    return "\n".join(f"- {r}" for r in combined)

# ---------------------------------------------------------------------------
# Runtime context for action execution
# ---------------------------------------------------------------------------

ALLOWED_ACTION_TYPES = {
    "generate_class_file",
    "git_commit_and_push",
    "generate_test_file",
    "continue"
}


@dataclass
class ActionRuntimeContext:
    """
    Objects and configuration that actions may need at runtime.
    This keeps 'main()' thin and the dispatcher generic.
    """
    project_root: Path
    class_generator: ClassGenerator
    git_manager: GitManager
    repo_config: RepoConfig
    logger: Any  # logging.Logger


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------

from core.actions.registry import ActionRegistry
from core.actions.base_action import ActionContext

def execute_actions(actions_list: list, ctx: ActionContext) -> None:
    logger = ctx.logger

    for index, raw in enumerate(actions_list, start=1):
        action = ActionRegistry.create(raw)
        if action is None:
            logger.warning(
                f"Unknown or unregistered action '{raw.get('type')}'. "
                f"Allowed: {ActionRegistry.allowed_types()}"
            )
            continue

        if not action.validate():
            logger.warning(f"Invalid params for action '{action.action_type}': {raw}")
            continue

        logger.info(f"Executing action #{index}: {action.action_type}")
        action.execute(ctx)

# ---------------------------------------------------------------------------
# Main entry point from main.py
# ---------------------------------------------------------------------------

def main(
    profile_name,
    class_name,
    task_description,
    refactor_class,
    agent_input,
    run_item,
    run_params,
):
    """
    High-level orchestration:

    1. Build runtime / Git / AI clients.
    2. Build agent_input (runtime info + optional refactor code).
    3. Inject ${agent_input}, ${task_description}, ${rules_block} into run_params['messages'].
    4. Call OpenAI, expecting an 'agent' JSON object.
    5. Execute actions returned under agent.actions[].
    """
    project_root = Path(__file__).resolve().parents[1]
    logger = BasicLogger(__name__).get_logger()
    logger.info("Starting AI action dispatcher app")

    # --- GIT SETUP -----------------------------------------------------
    repo_config = RepoConfig(
        repo_path=str(project_root),
        default_branch="master",
        remote_name="origin",
        author_name="Onat Agent",
        author_email="onat@gegeoglu.com",
    )
    git_client = GitClient(repo_path=repo_config.repo_path)
    git_manager = GitManager(git_client=git_client)

    # --- OPENAI CLIENT SETUP -------------------------------------------
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in .env")

    client = OpenAIClient(api_key=api_key)

    # --- BUILD agent_input RUNTIME OBJECT ------------------------------
    agent_input_obj: Dict[str, Any] = {
        "profile_name": profile_name,
        "class_name": class_name or None,
        "refactor_class": refactor_class or None,
    }

    # If refactor_class is provided, read its current content so the model
    # does not have to perform filesystem I/O.
    if refactor_class:
        reader = PythonFileReader(refactor_class)
        try:
            original_code = reader.read_file()
        except Exception as exc:
            logger.error(f"Could not read refactor_class '{refactor_class}': {exc}")
            original_code = ""

        agent_input_obj["refactor"] = {
            "file_path": refactor_class,
            "original_code": original_code,
        }

    # Merge any extra agent_input passed from the run (optional)
    if isinstance(agent_input, dict) and agent_input:
        agent_input_obj.update(agent_input)

    if run_item.target_file:
        agent_input_obj["target_file"] = run_item.target_file    

    # --- RULES + PLACEHOLDER INJECTION ---------------------------------
    # run_params MUST already be a valid OpenAI payload:
    # {
    #   "model": "...",
    #   "messages": [...],
    #   "temperature": ...,
    #   ...
    # }
    agent_input_json = json.dumps(agent_input_obj, ensure_ascii=False, indent=2)
    rules_block = build_rules_block_for_run(run_item)

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

    # 🔒 New: inject target_file
        if "${target_file}" in content:
            content = content.replace("${target_file}", run_item.target_file or "")

        msg["content"] = content


    logger.info(f"Calling OpenAI for profile '{profile_name}'")
    response = client.send_request(body=run_params)

    # --- PARSE AGENT + ACTIONS -----------------------------------------
    agent_obj = AIResponseParser.extract_agent(response)
    if not agent_obj:
        logger.error("Model did not return a valid 'agent' object. Aborting.")
        return

    actions = agent_obj.get("actions", [])
    if not isinstance(actions, list) or not actions:
        logger.warning(
            "No actions returned by the model. Parsed agent object: %r", agent_obj
        )
        return

    # --- EXECUTE ACTIONS -----------------------------------------------
    runtime_ctx = ActionRuntimeContext(
        project_root=project_root,
        class_generator=ClassGenerator(base_path=str(project_root)),
        git_manager=git_manager,
        repo_config=repo_config,
        logger=logger,
    )

    execute_actions(actions, runtime_ctx)
    logger.info("All actions executed.")

