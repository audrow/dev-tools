#!/usr/bin/env python3
import glob
import os
import sys
import pyperclip
import argparse
from typing import List, Optional, Tuple

DEFAULT_EXCLUDE_DIRS = ["node_modules", "venv", ".venv", "__pycache__", ".git", "build", "dist"]

def _generate_tree_structure(paths: List[str]) -> str:
    """Generates a tree-like string representation of the given file paths."""
    tree = {}
    for path in paths:
        parts = path.split(os.sep)
        current = tree
        for part in parts:
            current = current.setdefault(part, {})
    
    lines = []
    
    def _build_tree_string(current_node, prefix=""):
        # Sort keys: directories first, then files? Or just alphabetical?
        # Usually directories first or mixed alphabetical. Let's do alphabetical.
        keys = sorted(current_node.keys())
        for i, key in enumerate(keys):
            is_last = (i == len(keys) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{key}")
            
            # Recurse if there are children
            children = current_node[key]
            if children:
                extension = "    " if is_last else "│   "
                _build_tree_string(children, prefix + extension)

    _build_tree_string(tree)
    return "\n".join(lines) + "\n"

def aggregate_text(
    path_patterns: List[str],
    include_extensions: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    exclude_directories: Optional[List[str]] = None,
    output_file: Optional[str] = None,
    no_copy: bool = False,
) -> Tuple[Optional[str], List[str]]:
    """
    Aggregates text from files matching given path patterns and file extensions.

    Args:
        path_patterns: A list of path patterns to search for files (e.g., ["**/*.txt"]).
        include_extensions: A list of file extensions to include (e.g., [".txt", ".md"])
        exclude_extensions: A list of file extensions to exclude (e.g., [".log"])
        exclude_directories: A list of directory names to exclude (e.g., ["node_modules"]).
                             Defaults to DEFAULT_EXCLUDE_DIRS if None.
        output_file: The path to a file to write the aggregated text to. If None, the text is copied to the clipboard.
        no_copy: If True, the aggregated text will not be copied to the clipboard.

    Returns:
        A tuple containing:
        - The aggregated text as a string (or None if output_file is provided).
        - A list of the paths of the files that were processed.

    Raises:
        pyperclip.PyperclipException: If clipboard copy is requested but fails.
    """
    if exclude_directories is None:
        exclude_directories = DEFAULT_EXCLUDE_DIRS

    all_files = []
    for pattern in path_patterns:
        all_files.extend(glob.glob(pattern, recursive=True))
    
    # Remove duplicates and sort
    files = sorted(list(set(all_files)))
    processed_files = []
    
    # First pass: identify valid files to build structure
    valid_files = []
    for file in files:
        if include_extensions and not any(file.endswith(ext) for ext in include_extensions):
            continue
        if exclude_extensions and any(file.endswith(ext) for ext in exclude_extensions):
            continue
        path_parts = os.path.normpath(file).split(os.sep)
        if any(part in exclude_directories for part in path_parts):
            continue
        if os.path.isdir(file):
            continue
        valid_files.append(file)

    aggregated_text = ""
    if valid_files:
        aggregated_text += "========================================\n"
        aggregated_text += "FILE STRUCTURE:\n"
        aggregated_text += _generate_tree_structure(valid_files)
        aggregated_text += "========================================\n\n"

    for file in valid_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                aggregated_text += f"--- START OF FILE: {file} ---\n"
                aggregated_text += content
                aggregated_text += f"\n--- END OF FILE: {file} ---\n\n"
            processed_files.append(file)
        except Exception as e:
            print(f"Error reading file {file}: {e}")

    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(aggregated_text)
            return None, processed_files
        except Exception as e:
            print(f"Error writing to file {output_file}: {e}")
            return None, processed_files
    else:
        if not no_copy:
            pyperclip.copy(aggregated_text)
        return aggregated_text, processed_files

def main():
    parser = argparse.ArgumentParser(description="Aggregate text from files.")
    parser.add_argument("path_patterns", type=str, nargs="+", help="The path patterns to search for files (e.g., \"**/*.txt\").")
    parser.add_argument("-i", "--include-extensions", nargs="*", help="A list of file extensions to include (e.g., \".txt\" \".md\").")
    parser.add_argument("-e", "--exclude-extensions", nargs="*", help="A list of file extensions to exclude (e.g., \".log\").")
    parser.add_argument("-d", "--exclude-directories", nargs="*", help=f"A list of directory names to exclude. Defaults to {DEFAULT_EXCLUDE_DIRS}.")
    parser.add_argument("-o", "--output-file", type=str, help="The path to a file to write the aggregated text to. If not provided, the text is copied to the clipboard.")
    parser.add_argument("--no-copy", action="store_true", help="Do not copy the aggregated text to the clipboard.")
    parser.add_argument("-s", "--stdout", action="store_true", help="Print the aggregated text to standard output (implies --no-copy).")

    args = parser.parse_args()

    # If stdout is requested, disable clipboard copy
    if args.stdout:
        args.no_copy = True

    try:
        text, processed_files = aggregate_text(
            path_patterns=args.path_patterns,
            include_extensions=args.include_extensions,
            exclude_extensions=args.exclude_extensions,
            exclude_directories=args.exclude_directories,
            output_file=args.output_file,
            no_copy=args.no_copy,
        )
    except pyperclip.PyperclipException as e:
        print(f"Error: Could not copy to clipboard.\nDetails: {e}")
        print("Tip: If you are running in a headless environment (e.g., SSH, Docker) without X11 forwarding, the clipboard cannot be accessed. Try using --output-file or --no-copy.")
        sys.exit(1)

    if args.stdout:
        if text:
            print(text)
        elif args.output_file:
             # If written to file but stdout requested, we can't easily print it unless we read it back or change logic.
             # For now, let's assume stdout implies "don't use output_file" or just print nothing if output_file consumed it.
             pass
        return

    print(f"Found {len(processed_files)} files:")
    for file in processed_files:
        print(f"  - {file}")
    
    print("-" * 20)

    if args.output_file:
        print(f"Successfully written to {args.output_file}")
    elif not args.no_copy:
        if text:
            print(f"Successfully copied to clipboard ({len(text)} characters)")
        else:
            print("No text found to copy.")
    else:
        print("Aggregation complete. (Clipboard copy disabled)")

if __name__ == "__main__":
    main()
