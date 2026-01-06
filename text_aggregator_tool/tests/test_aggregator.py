import os
import unittest
import json
import sys
from unittest.mock import patch, MagicMock
from text_aggregator.aggregator import aggregate_text, load_config, main
import tempfile
import shutil

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
        os.makedirs(os.path.dirname(os.path.join(self.test_dir, filename)), exist_ok=True)
        with open(os.path.join(self.test_dir, filename), "w") as f:
            f.write(content)

    def test_aggregate_format(self):
        aggregated_text, files = aggregate_text(["**/*.txt"], no_copy=True)
        self.assertIn("FILE STRUCTURE:", aggregated_text)
        self.assertIn("--- START OF FILE: file1.txt ---", aggregated_text)

    def test_extension_normalization(self):
        self.create_test_file("script.py", "print('hello')")
        text, files = aggregate_text(["**/*"], include_extensions=["py"], no_copy=True)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("script.py"))

    def test_comma_separated_extensions(self):
        # We test the parsing logic in main by mocking sys.argv
        with patch("sys.argv", ["text-aggregator", "-i", "py,txt", "--no-copy"]):
            with patch("text_aggregator.aggregator.aggregate_text", return_value=("", [])) as mock_agg:
                main()
                args, kwargs = mock_agg.call_args
                self.assertEqual(kwargs["include_extensions"], ["py", "txt"])

    def test_default_path_pattern(self):
        # Test that main uses ["**/*"] when no path is provided
        with patch("sys.argv", ["text-aggregator", "--no-copy"]):
            with patch("text_aggregator.aggregator.aggregate_text", return_value=("", [])) as mock_agg:
                main()
                args, kwargs = mock_agg.call_args
                self.assertEqual(kwargs["path_patterns"], ["**/*"])

if __name__ == "__main__":
    unittest.main()