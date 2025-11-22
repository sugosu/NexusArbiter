import os
from pathlib import Path

OUTPUT_FILE = "ALL_PY.txt"

def collect_all_files(root: Path):
    collected_parts = []

    for file_path in root.rglob("*.py"):
        # avoid including the output file itself
        if file_path.name == OUTPUT_FILE:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        header = f"# === FILE: {file_path.relative_to(root)} ===\n"
        collected_parts.append(header + content + "\n\n")

    return collected_parts


if __name__ == "__main__":
    root = Path(".").resolve()
    blocks = collect_all_files(root)

    output_path = root / OUTPUT_FILE
    output_path.write_text("".join(blocks), encoding="utf-8")

    print(f"Collected all .py files into: {output_path}")
