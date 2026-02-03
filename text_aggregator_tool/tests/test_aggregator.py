import os
import unittest
import json
import sys
from unittest.mock import patch, MagicMock, mock_open
from text_aggregator.aggregator import aggregate_text, load_config, main
import tempfile
import shutil
import io


class TestAggregator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.create_test_file("file1.txt", "This is file 1.")
        self.create_test_file("sub/file2.txt", "This is file 2.")

        self.cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.test_dir)

    def create_test_file(self, filename, content):
        # Ensure dir exists
        os.makedirs(
            os.path.dirname(os.path.join(self.test_dir, filename)), exist_ok=True
        )
        with open(os.path.join(self.test_dir, filename), "w") as f:
            f.write(content)

    def test_aggregate_format(self):
        aggregated_text, files = aggregate_text(["**/*.txt"], no_copy=True)
        self.assertIn("FILE STRUCTURE:", aggregated_text)
        self.assertIn("--- START OF FILE: file1.txt ---", aggregated_text)
        self.assertIn("This is file 1.", aggregated_text)

    def test_exclude_directories(self):
        os.makedirs("node_modules")
        self.create_test_file("node_modules/hidden.txt", "hidden")
        # node_modules is in default_config.json which we can't easily read in this temp env
        # unless we mock it or rely on it being present.
        # Let's pass explicit excludes to test logic.
        aggregated_text, files = aggregate_text(
            ["**/*"], exclude_directories=["node_modules"], no_copy=True
        )
        self.assertNotIn("node_modules/hidden.txt", files)

    def test_extension_normalization(self):
        self.create_test_file("script.py", "print('hello')")
        text, files = aggregate_text(["**/*"], include_extensions=["py"], no_copy=True)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("script.py"))

    def test_config_loading_precedence(self):
        # We need to mock os.path.exists and open to simulate config files
        # 1. Package config exists
        # 2. Global config exists

        package_config = {"exclude_directories": ["pkg_exclude"], "no_copy": False}
        global_config = {"exclude_directories": ["global_exclude"], "no_copy": True}

        with patch("os.path.dirname", return_value="/pkg"), patch(
            "os.path.expanduser", return_value="/home/user"
        ), patch("os.path.exists") as mock_exists, patch(
            "builtins.open", mock_open()
        ) as mock_file:

            mock_exists.side_effect = lambda p: p in [
                "/pkg/default_config.json",
                "/home/user/.text_aggregator.json",
            ]

            # We need mock_open to return different contents based on file path
            # This is tricky with simple mock_open. Let's patch json.load instead.
            with patch("json.load") as mock_json_load:
                mock_json_load.side_effect = [package_config, global_config]

                config = load_config()

                # Global should override package
                # But lists are updated/replaced?
                # The code does config.update(). So keys are replaced.
                self.assertEqual(config["exclude_directories"], ["global_exclude"])
                self.assertTrue(config["no_copy"])

    def test_main_stdout(self):
        # Verify that with --stdout, it prints text and nothing else
        with patch("sys.argv", ["text-aggregator", "-s"]), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as mock_stdout, patch(
            "text_aggregator.aggregator.aggregate_text"
        ) as mock_agg:

            mock_agg.return_value = ("AGGREGATED TEXT", ["file1.txt"])

            main()

            output = mock_stdout.getvalue()
            self.assertIn("AGGREGATED TEXT", output)
            self.assertNotIn("Found 1 files", output)  # Should NOT print status
            self.assertNotIn("Clipboard", output)

    def test_comma_separated_extensions_in_main(self):
        with patch("sys.argv", ["text-aggregator", "-i", "py,txt", "--no-copy"]), patch(
            "text_aggregator.aggregator.aggregate_text", return_value=("", [])
        ) as mock_agg:
            main()
            args, kwargs = mock_agg.call_args
            self.assertEqual(kwargs["include_extensions"], ["py", "txt"])

    def test_exclude_files(self):
        """Test that specific files can be excluded by name."""
        self.create_test_file("package-lock.json", '{"lockfileVersion": 1}')
        self.create_test_file("package.json", '{"name": "test"}')

        aggregated_text, files = aggregate_text(
            ["**/*.json"],
            exclude_files=["package-lock.json"],
            respect_gitignore=False,
            no_copy=True,
        )

        # package.json should be included, package-lock.json should not
        file_basenames = [os.path.basename(f) for f in files]
        self.assertIn("package.json", file_basenames)
        self.assertNotIn("package-lock.json", file_basenames)

    def test_exclude_files_multiple(self):
        """Test that multiple files can be excluded."""
        self.create_test_file("yarn.lock", "# yarn lockfile")
        self.create_test_file("poetry.lock", "[[package]]")
        self.create_test_file("README.md", "# Readme")

        aggregated_text, files = aggregate_text(
            ["**/*"],
            exclude_files=["yarn.lock", "poetry.lock"],
            respect_gitignore=False,
            no_copy=True,
        )

        file_basenames = [os.path.basename(f) for f in files]
        self.assertNotIn("yarn.lock", file_basenames)
        self.assertNotIn("poetry.lock", file_basenames)
        self.assertIn("README.md", file_basenames)

    def test_respect_gitignore(self):
        """Test that .gitignore patterns are respected."""
        # Create a .gitignore file
        self.create_test_file(".gitignore", "*.log\nbuild/\n")
        self.create_test_file("app.py", "print('hello')")
        self.create_test_file("debug.log", "log content")
        os.makedirs(os.path.join(self.test_dir, "build"), exist_ok=True)
        self.create_test_file("build/output.js", "compiled")

        aggregated_text, files = aggregate_text(
            ["**/*"],
            exclude_directories=[],
            exclude_files=[],
            respect_gitignore=True,
            no_copy=True,
        )

        file_basenames = [os.path.basename(f) for f in files]
        self.assertIn("app.py", file_basenames)
        self.assertNotIn("debug.log", file_basenames)
        self.assertNotIn("output.js", file_basenames)

    def test_respect_gitignore_disabled(self):
        """Test that .gitignore can be disabled."""
        self.create_test_file(".gitignore", "*.log\n")
        self.create_test_file("debug.log", "log content")
        self.create_test_file("app.py", "print('hello')")

        aggregated_text, files = aggregate_text(
            ["**/*"],
            exclude_directories=[],
            exclude_files=[],
            respect_gitignore=False,
            no_copy=True,
        )

        file_basenames = [os.path.basename(f) for f in files]
        self.assertIn("debug.log", file_basenames)
        self.assertIn("app.py", file_basenames)

    def test_main_no_gitignore_flag(self):
        """Test that --no-gitignore flag is passed correctly."""
        with patch(
            "sys.argv", ["text-aggregator", "--no-gitignore", "--no-copy"]
        ), patch(
            "text_aggregator.aggregator.aggregate_text", return_value=("", [])
        ) as mock_agg:
            main()
            args, kwargs = mock_agg.call_args
            self.assertFalse(kwargs["respect_gitignore"])

    def test_main_exclude_files_flag(self):
        """Test that -f/--exclude-files flag is passed correctly."""
        with patch(
            "sys.argv", ["text-aggregator", "-f", "lock.json", "yarn.lock", "--no-copy"]
        ), patch(
            "text_aggregator.aggregator.aggregate_text", return_value=("", [])
        ) as mock_agg:
            main()
            args, kwargs = mock_agg.call_args
            self.assertEqual(kwargs["exclude_files"], ["lock.json", "yarn.lock"])


if __name__ == "__main__":
    unittest.main()
