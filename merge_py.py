import os
import json

OUTPUT_NAME = "merged_all.txt"

def collect_all_files(root_dir, output_name):
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            # include .py and .json
            if fname.endswith((".py", ".json")) and fname != output_name:
                files.append(os.path.join(dirpath, fname))
    return files


def merge_all(files, output_path):
    with open(output_path, "w", encoding="utf-8") as out:
        for f in files:
            out.write("\n")
            out.write("=" * 80 + "\n")
            out.write(f"FILE: {f}\n")
            out.write("=" * 80 + "\n\n")

            try:
                with open(f, "r", encoding="utf-8") as src:
                    content = src.read()
                out.write(content)
            except Exception as e:
                out.write(f"!! ERROR READING FILE: {e} !!")

            out.write("\n\n")

    print(f"Merged {len(files)} files into: {output_path}")


if __name__ == "__main__":
    root = os.getcwd()
    files = collect_all_files(root, OUTPUT_NAME)
    output_file = os.path.join(root, OUTPUT_NAME)
    merge_all(files, output_file)
