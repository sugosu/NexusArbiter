import os
import json

OUTPUT_NAME = "merged_all.txt"

def collect_all_files(root_dir, output_name):
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            # include .py and .json but skip output file
            if fname.endswith((".py", ".json")) and fname != output_name:
                full_path = os.path.join(dirpath, fname)
                files.append(full_path)
    return files


def merge_all(files, output_path):
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
    root = os.getcwd()
    files = collect_all_files(root, OUTPUT_NAME)
    output_file = os.path.join(root, OUTPUT_NAME)
    merge_all(files, output_file)
