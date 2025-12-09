import os
import json
import sys

OUTPUT_NAME = "merged_all.txt"
LICENSE_NAME = "LICENSE"   # included explicitly

# <<< SET THIS TO YOUR GENERATED PROJECT ROOT (relative or absolute) >>>
DEFAULT_ROOT_DIR = "./expense_tracker"  # e.g. "expense_tracker" or "/full/path/to/expense_tracker"


def collect_all_files(root_dir: str, output_name: str) -> list[str]:
    files: list[str] = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:

            # Include LICENSE explicitly
            if fname == LICENSE_NAME:
                full_path = os.path.join(dirpath, fname)
                files.append(full_path)
                continue

            # Include .py and .json but skip output file
            if fname.endswith((".py", ".json")) and fname != output_name:
                full_path = os.path.join(dirpath, fname)
                files.append(full_path)

    return files


def merge_all(files: list[str], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as out:
        for fpath in files:
            rel_path = os.path.relpath(fpath)

            # HEADER
            out.write("\n")
            out.write("#" * 90 + "\n")
            out.write(f"# FILE: {rel_path}\n")
            out.write("#" * 90 + "\n\n")

            # CONTENT
            try:
                with open(fpath, "r", encoding="utf-8") as src:
                    content = src.read()
                out.write(content)
            except Exception as e:
                out.write(f"!! ERROR READING FILE: {e} !!")

            out.write("\n\n")  # separator between files

    print(f"Merged {len(files)} files into: {output_path}")


if __name__ == "__main__":
    # If a path is provided as first argument, use that.
    # Otherwise fall back to DEFAULT_ROOT_DIR.
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = DEFAULT_ROOT_DIR

    root_dir = os.path.abspath(root_dir)
    output_file = os.path.join(root_dir, OUTPUT_NAME)

    files = collect_all_files(root_dir, OUTPUT_NAME)
    merge_all(files, output_file)
