import glob
import pyperclip
import argparse
from typing import List, Optional

def aggregate_text(
    path_pattern: str,
    include_extensions: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    output_file: Optional[str] = None,
) -> Optional[str]:
    """
    Aggregates text from files matching a given path pattern and file extensions.

    Args:
        path_pattern: The path pattern to search for files (e.g., "**/*.txt").
        include_extensions: A list of file extensions to include (e.g., [".txt", ".md"])
        exclude_extensions: A list of file extensions to exclude (e.g., [".log"])
        output_file: The path to a file to write the aggregated text to. If None, the text is copied to the clipboard.

    Returns:
        The aggregated text as a string, or None if an output file is specified.
    """
    files = sorted(glob.glob(path_pattern, recursive=True))
    aggregated_text = ""

    for file in files:
        if include_extensions and not any(file.endswith(ext) for ext in include_extensions):
            continue
        if exclude_extensions and any(file.endswith(ext) for ext in exclude_extensions):
            continue
        try:
            with open(file, "r", encoding="utf-8") as f:
                aggregated_text += f.read() + "\n\n"
        except Exception as e:
            print(f"Error reading file {file}: {e}")

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(aggregated_text)
            return None
        except Exception as e:
            print(f"Error writing to file {output_file}: {e}")
            return None
    else:
        try:
            pyperclip.copy(aggregated_text)
        except pyperclip.PyperclipException:
            print("Warning: Could not copy to clipboard. `xclip` or `xsel` may not be installed.")
        return aggregated_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate text from files.")
    parser.add_argument("path_pattern", type=str, help="The path pattern to search for files (e.g., \"**/*.txt\").")
    parser.add_argument("--include-extensions", nargs="*", help="A list of file extensions to include (e.g., \".txt\" \".md\").")
    parser.add_argument("--exclude-extensions", nargs="*", help="A list of file extensions to exclude (e.g., \".log\").")
    parser.add_argument("--output-file", type=str, help="The path to a file to write the aggregated text to. If not provided, the text is copied to the clipboard.")

    args = parser.parse_args()

    result = aggregate_text(
        path_pattern=args.path_pattern,
        include_extensions=args.include_extensions,
        exclude_extensions=args.exclude_extensions,
        output_file=args.output_file,
    )

    if result:
        print(result)
