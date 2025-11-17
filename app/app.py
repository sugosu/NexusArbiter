# app/app.py
from __future__ import annotations

import os
from pathlib import Path

from core.ai_client.ai_client import OpenAIClient
from core.ai_client.api_param_generator import AIParamGenerator
from core.ai_client.ai_profile_loader import AIProfileLoader
from core.ai_client.ai_response_parser import AIResponseParser
from core.files.class_generator import ClassGenerator
from core.files.class_reader import PythonFileReader


def main(profile_name: str, class_name: str = "", refactor_class: str = "") -> None:
    project_root = Path(__file__).resolve().parents[1]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in .env")

    client = OpenAIClient(api_key=api_key)

    # Load preset profiles
    profiles_dir = project_root / "profiles"
    profile_loader = AIProfileLoader(
        profiles_dir=profiles_dir,
        default_user="onat",
    )

    presets = profile_loader.load_profiles()

    if profile_name not in presets:
        raise ValueError(
            f"Profile '{profile_name}' not found. "
            f"Available profiles: {', '.join(presets.keys())}"
        )

    if not class_name:
        class_name = "namenotmentioned.py"

    param_gen = AIParamGenerator(
        client=client,
        presets=presets,
        default_user="onat",
    )

    # ------------------------------------------------------------------
    # REFACTOR MODE: when --refactorclass is provided
    # ------------------------------------------------------------------
    if refactor_class:
        # 1) Read existing file content
        reader = PythonFileReader(refactor_class)
        class_str = reader.read_file()

        # 2) Build params from preset (keeps system message + response_format)
        params = param_gen.build_params(profile_name)

        # 3) Inject class content into the ${class_content} placeholder
        for msg in params.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str) and "${class_content}" in content:
                msg["content"] = content.replace("${class_content}", class_str)

        # 4) Call OpenAI
        response = client.send_request(body=params)

        # 5) Parse JSON response (expects {"code": "...", "context": "..."})
        parsed = AIResponseParser.extract(response)
        code_str = parsed["code"]
        context_str = parsed.get("context", "")

        # 6) Write refactored file
        generator = ClassGenerator(base_path=str(project_root))
        out_name = class_name or "refactored.py"
        file_path = generator.generate_with_comments(out_name, code_str, context_str)

        print(f"Refactored file created: {file_path}")
        return

    # ------------------------------------------------------------------
    # NORMAL GENERATION MODE
    # ------------------------------------------------------------------
    # Build selected profile request
    params = param_gen.build_params(profile_name)

    # OPTIONAL: replace "${prompt}" in messages (placeholder logic)
    for msg in params.get("messages", []):
        if msg.get("role") == "user" and "${prompt}" in msg.get("content", ""):
            msg["content"] = "Generate a simple calculator class."  # adjust later

    # Call OpenAI
    response = client.send_request(body=params)

    # Parse
    parsed = AIResponseParser.extract(response)
    code_str = parsed["code"]
    context_str = parsed.get("context", "")

    # Write file
    generator = ClassGenerator(base_path=str(project_root))
    file_path = generator.generate_with_comments(
        class_name,
        code_str,
        context_str,
    )

    print(f"Created: {file_path}")
