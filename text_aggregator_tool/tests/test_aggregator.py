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
        os.makedirs(os.path.dirname(os.path.join(self.test_dir, filename)), exist_ok=True)
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
        aggregated_text, files = aggregate_text(["**/*"], exclude_directories=["node_modules"], no_copy=True)
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
        
        with patch("os.path.dirname", return_value="/pkg"), \
             patch("os.path.expanduser", return_value="/home/user"), \
             patch("os.path.exists") as mock_exists, \
             patch("builtins.open", mock_open()) as mock_file:
            
            mock_exists.side_effect = lambda p: p in ["/pkg/default_config.json", "/home/user/.text_aggregator.json"]
            
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
        with patch("sys.argv", ["text-aggregator", "-s"]), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, \
             patch("text_aggregator.aggregator.aggregate_text") as mock_agg:
            
            mock_agg.return_value = ("AGGREGATED TEXT", ["file1.txt"])
            
            main()
            
            output = mock_stdout.getvalue()
            self.assertIn("AGGREGATED TEXT", output)
            self.assertNotIn("Found 1 files", output) # Should NOT print status
            self.assertNotIn("Clipboard", output)

    def test_comma_separated_extensions_in_main(self):
        with patch("sys.argv", ["text-aggregator", "-i", "py,txt", "--no-copy"]), \
             patch("text_aggregator.aggregator.aggregate_text", return_value=("", [])) as mock_agg:
            main()
            args, kwargs = mock_agg.call_args
            self.assertEqual(kwargs["include_extensions"], ["py", "txt"])

if __name__ == "__main__":
    unittest.main()