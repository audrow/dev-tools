import os
import unittest
import json
from unittest.mock import patch
from text_aggregator.aggregator import aggregate_text, load_config
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

    def test_exclude_directories_from_package_default(self):
        # venv should be excluded by package default (if default_config.json is found)
        os.makedirs("venv")
        self.create_test_file("venv/hidden.txt", "hidden")
        aggregated_text, files = aggregate_text(["**/*"], no_copy=True)
        self.assertNotIn("venv/hidden.txt", files)

    def test_extension_normalization(self):
        self.create_test_file("script.py", "print('hello')")
        text, files = aggregate_text(["**/*"], include_extensions=["py"], no_copy=True)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("script.py"))

    def test_global_config_overrides_package_default(self):
        # Create a fake home directory
        home_dir = os.path.join(self.test_dir, "fake_home")
        os.makedirs(home_dir)
        
        # Create global config that overrides exclude_directories
        global_config_data = {
            "exclude_directories": ["other_dir"] 
        }
        with open(os.path.join(home_dir, ".text_aggregator.json"), "w") as f:
            json.dump(global_config_data, f)

        # Mock expanduser to point to fake home
        with patch("os.path.expanduser", return_value=home_dir):
            # Create a 'venv' dir and a file in it
            os.makedirs("venv")
            self.create_test_file("venv/visible.txt", "I should be visible now")
            
            # Since global config overrides package default, venv is no longer excluded
            text, files = aggregate_text(["**/*"], no_copy=True)
            self.assertIn("venv/visible.txt", files)
            self.assertIn("I should be visible now", text)

    def test_full_config_options(self):
        # Create a fake home directory
        home_dir = os.path.join(self.test_dir, "fake_home_full")
        os.makedirs(home_dir)
        
        # Create global config with all options
        global_config_data = {
            "output_file": "default_output.txt",
            "no_copy": True,
            "stdout": True
        }
        with open(os.path.join(home_dir, ".text_aggregator.json"), "w") as f:
            json.dump(global_config_data, f)

        # Mock expanduser to point to fake home
        with patch("os.path.expanduser", return_value=home_dir):
            config = load_config()
            self.assertEqual(config["output_file"], "default_output.txt")
            self.assertTrue(config["no_copy"])
            self.assertTrue(config["stdout"])

if __name__ == "__main__":
    unittest.main()
