# app.py
import os
from dotenv import load_dotenv
from core.ai_client.ai_client import OpenAIClient
from core.ai_client.api_param_generator import AIParamGenerator
from core.ai_client.ai_response_parser import AIResponseParser
from core.files.class_generator import ClassGenerator


def main():
    # 1) Init the AI agent (HTTP client)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "")
    client = OpenAIClient(api_key=api_key)

    # 2) Build parameters (payload) using the parameter generator
    param_gen = AIParamGenerator(client=client, default_user="onat")
    body = param_gen.build_code_generation()

    # 3) Call the AI agent with the built parameters
    response = client.send_request(body=body)

    # 4) Extract code + context from the response
    parsed = AIResponseParser.extract(response)
    code_str = parsed["code"]
    context_str = parsed["context"]

    # 5) Generate the .py file (with context as header comments)
    generator = ClassGenerator(base_path=r"C:\projects\aiAgency")
    file_path = generator.generate_with_comments(
        "commit_message_builder.py",
        code_str,
        context_str,
    )

    # 6) Print result info (and optional context)
    print(f"✅ File created: {file_path}")
    if context_str:
        print("Context embedded into file header.")


if __name__ == "__main__":
    main()
