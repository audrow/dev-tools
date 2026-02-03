#!/usr/bin/env python3
import glob
import os
import sys
import json
import pyperclip
import argparse
import pathspec
from typing import List, Optional, Tuple, Dict, Any

CONFIG_FILENAME = ".text_aggregator.json"


def load_config() -> Dict[str, Any]:
    """
    Loads configuration.
    Priority: Global Config (~/.text_aggregator.json) > Package Default (default_config.json).
    """
    config = {}

    # 1. Load Package Default Config
    package_config_path = os.path.join(os.path.dirname(__file__), "default_config.json")
    if os.path.exists(package_config_path):
        try:
            with open(package_config_path, "r") as f:
                config.update(json.load(f))
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse package config {package_config_path}: {e}")

    # 2. Load Global Config (~/.text_aggregator.json)
    global_config_path = os.path.join(os.path.expanduser("~"), CONFIG_FILENAME)
    if os.path.exists(global_config_path):
        try:
            with open(global_config_path, "r") as f:
                config.update(json.load(f))
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse global config {global_config_path}: {e}")

    return config


def _normalize_extensions(extensions: Optional[List[str]]) -> Optional[List[str]]:
    """Ensures all extensions start with a dot."""
    if not extensions:
        return extensions
    return [ext if ext.startswith(".") else f".{ext}" for ext in extensions]


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
        keys = sorted(current_node.keys())
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{key}")

            children = current_node[key]
            if children:
                extension = "    " if is_last else "│   "
                _build_tree_string(children, prefix + extension)

    _build_tree_string(tree)
    return "\n".join(lines) + "\n"


def _load_gitignore_spec(start_path: str) -> Optional[pathspec.PathSpec]:
    """
    Loads .gitignore patterns from the directory containing start_path or its parents.
    Returns a PathSpec object for matching, or None if no .gitignore found.
    """
    # Find the directory to start searching from
    if os.path.isfile(start_path):
        search_dir = os.path.dirname(os.path.abspath(start_path))
    else:
        search_dir = os.path.abspath(start_path)

    # Look for .gitignore in current directory and parent directories
    patterns = []
    current_dir = search_dir if search_dir else os.getcwd()

    # Walk up to find .gitignore files (child .gitignore patterns take precedence)
    gitignore_files = []
    while True:
        gitignore_path = os.path.join(current_dir, ".gitignore")
        if os.path.exists(gitignore_path):
            gitignore_files.append(gitignore_path)

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # Reached root
            break
        current_dir = parent_dir

    # Read patterns from all found .gitignore files (parent first, then child)
    for gitignore_path in reversed(gitignore_files):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                patterns.extend(f.readlines())
        except Exception:
            pass

    if not patterns:
        return None

    return pathspec.PathSpec.from_lines("gitignore", patterns)


def aggregate_text(
    path_patterns: List[str],
    include_extensions: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    exclude_directories: Optional[List[str]] = None,
    exclude_files: Optional[List[str]] = None,
    respect_gitignore: bool = True,
    output_file: Optional[str] = None,
    no_copy: bool = False,
) -> Tuple[Optional[str], List[str]]:
    """
    Aggregates text from files matching given path patterns and file extensions.

    Args:
        path_patterns: A list of path patterns to search for files (e.g., ["**/*.txt"]).
        include_extensions: A list of file extensions to include (e.g., [".txt", "md"]).
        exclude_extensions: A list of file extensions to exclude (e.g., ["log"]).
        exclude_directories: A list of directory names to exclude (e.g., ["node_modules"]).
                             Defaults to package/global config if None.
        exclude_files: A list of file names to exclude (e.g., ["package-lock.json"]).
                       Defaults to package/global config if None.
        respect_gitignore: If True, files matching .gitignore patterns will be excluded.
        output_file: The path to a file to write the aggregated text to. If None, the text is copied to the clipboard.
        no_copy: If True, the aggregated text will not be copied to the clipboard.

    Returns:
        A tuple containing:
        - The aggregated text as a string (or None if output_file is provided).
        - A list of the paths of the files that were processed.

    Raises:
        pyperclip.PyperclipException: If clipboard copy is requested but fails.
    """
    # Load defaults if not provided
    config = load_config()
    if exclude_directories is None:
        exclude_directories = config.get("exclude_directories", [])
    if exclude_files is None:
        exclude_files = config.get("exclude_files", [])

    # Normalize extensions
    include_extensions = _normalize_extensions(include_extensions)
    exclude_extensions = _normalize_extensions(exclude_extensions)

    all_files = []
    for pattern in path_patterns:
        all_files.extend(glob.glob(pattern, recursive=True))

    # Remove duplicates and sort
    files = sorted(list(set(all_files)))
    processed_files = []

    # Load gitignore spec if enabled
    gitignore_spec = None
    if respect_gitignore:
        gitignore_spec = _load_gitignore_spec(os.getcwd())

    # First pass: identify valid files to build structure
    valid_files = []
    for file in files:
        if include_extensions and not any(
            file.endswith(ext) for ext in include_extensions
        ):
            continue
        if exclude_extensions and any(file.endswith(ext) for ext in exclude_extensions):
            continue
        path_parts = os.path.normpath(file).split(os.sep)
        if any(part in exclude_directories for part in path_parts):
            continue
        # Check if the file basename matches any excluded file names
        if exclude_files and os.path.basename(file) in exclude_files:
            continue
        # Check against .gitignore patterns
        if gitignore_spec and gitignore_spec.match_file(file):
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
    config = load_config()

    parser = argparse.ArgumentParser(description="Aggregate text from files.")
    parser.add_argument(
        "path_patterns",
        type=str,
        nargs="*",
        help='The path patterns to search for files (e.g., "**/*.txt"). Defaults to "**/*".',
    )
    parser.add_argument(
        "-i",
        "--include-extensions",
        nargs="*",
        help='A list of file extensions to include (e.g., "txt,md").',
    )
    parser.add_argument(
        "-e",
        "--exclude-extensions",
        nargs="*",
        help='A list of file extensions to exclude (e.g., "log,tmp").',
    )
    parser.add_argument(
        "-d",
        "--exclude-directories",
        nargs="*",
        help="A list of directory names to exclude. Defaults to package/global config.",
    )
    parser.add_argument(
        "-f",
        "--exclude-files",
        nargs="*",
        help="A list of file names to exclude. Defaults to package/global config.",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Do not respect .gitignore patterns when excluding files.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        help="The path to a file to write the aggregated text to. If not provided, the text is copied to the clipboard.",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Do not copy the aggregated text to the clipboard.",
    )
    parser.add_argument(
        "-s",
        "--stdout",
        action="store_true",
        help="Print the aggregated text to standard output (implies --no-copy).",
    )

    args = parser.parse_args()

    # Determine final values (CLI > Config)
    path_patterns = args.path_patterns if args.path_patterns else ["**/*"]

    def _parse_exts(ext_list: Optional[List[str]]) -> Optional[List[str]]:
        if not ext_list:
            return ext_list
        parsed = []
        for item in ext_list:
            parsed.extend([x.strip() for x in item.split(",") if x.strip()])
        return parsed

    exclude_directories = args.exclude_directories
    if exclude_directories is None:
        exclude_directories = config.get("exclude_directories")

    exclude_files = args.exclude_files
    if exclude_files is None:
        exclude_files = config.get("exclude_files")

    # Determine respect_gitignore: CLI --no-gitignore overrides config
    if args.no_gitignore:
        respect_gitignore = False
    else:
        respect_gitignore = config.get("respect_gitignore", True)

    include_extensions = _parse_exts(args.include_extensions)
    if include_extensions is None:
        include_extensions = config.get("include_extensions")

    exclude_extensions = _parse_exts(args.exclude_extensions)
    if exclude_extensions is None:
        exclude_extensions = config.get("exclude_extensions")

    output_file = args.output_file
    if output_file is None:
        output_file = config.get("output_file")

    no_copy = args.no_copy
    if not no_copy:
        no_copy = config.get("no_copy", False)

    stdout = args.stdout
    if not stdout:
        stdout = config.get("stdout", False)

    # If stdout is requested, disable clipboard copy
    if stdout:
        no_copy = True

    try:
        text, processed_files = aggregate_text(
            path_patterns=path_patterns,
            include_extensions=include_extensions,
            exclude_extensions=exclude_extensions,
            exclude_directories=exclude_directories,
            exclude_files=exclude_files,
            respect_gitignore=respect_gitignore,
            output_file=output_file,
            no_copy=no_copy,
        )
    except pyperclip.PyperclipException as e:
        print(f"Error: Could not copy to clipboard.\nDetails: {e}")
        print(
            "Tip: If you are running in a headless environment (e.g., SSH, Docker) without X11 forwarding, the clipboard cannot be accessed. Try using --output-file or --no-copy."
        )
        sys.exit(1)

    if stdout:
        if text:
            print(text)
        return

    print(f"Found {len(processed_files)} files:")
    for file in processed_files:
        print(f"  - {file}")

    print("-" * 20)

    if output_file:
        print(f"Successfully written to {output_file}")
    elif not no_copy:
        if text:
            print(f"Successfully copied to clipboard ({len(text)} characters)")
        else:
            print("No text found to copy.")
    else:
        print("Aggregation complete. (Clipboard copy disabled)")


if __name__ == "__main__":
    main()
