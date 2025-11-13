# app/app.py
from __future__ import annotations

import os
from pathlib import Path

from core.ai_client.ai_client import OpenAIClient
from core.ai_client.api_param_generator import AIParamGenerator
from core.ai_client.ai_profile_loader import AIProfileLoader
from core.ai_client.ai_response_parser import AIResponseParser
from core.files.class_generator import ClassGenerator


def main(profile_name: str) -> None:
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

    param_gen = AIParamGenerator(
        client=client,
        presets=presets,
        default_user="onat",
    )

    # Build selected profile request
    params = param_gen.build_params(profile_name)

    # OPTIONAL: replace "${prompt}" in messages
    for msg in params.get("messages", []):
        if msg["role"] == "user" and "${prompt}" in msg["content"]:
            msg["content"] = "Generate a simple calculator class."  # or dynamic later

    # Call OpenAI
    response = client.send_request(body=params)

    # Parse
    parsed = AIResponseParser.extract(response)
    code_str = parsed["code"]
    context_str = parsed.get("context", "")

    # Write file
    generator = ClassGenerator(base_path=str(project_root))
    file_path = generator.generate_with_comments(
        "generated_class.py", code_str, context_str
    )

    print(f"Created: {file_path}")
