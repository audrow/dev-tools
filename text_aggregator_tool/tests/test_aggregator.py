import os
import unittest
from text_aggregator.aggregator import aggregate_text
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
        
        # Check for File Structure header
        self.assertIn("FILE STRUCTURE:", aggregated_text)
        
        # Check for Tree structure elements
        # Note: glob order might vary slightly, but file1.txt and sub should be there.
        # file1.txt might be '├── file1.txt' or '└── file1.txt' depending on order.
        self.assertTrue("├── file1.txt" in aggregated_text or "└── file1.txt" in aggregated_text)
        self.assertTrue("├── sub" in aggregated_text or "└── sub" in aggregated_text)
        # file2.txt is inside sub, so it should be indented
        self.assertTrue("    ├── file2.txt" in aggregated_text or "    └── file2.txt" in aggregated_text or "│   └── file2.txt" in aggregated_text)

        # Check for Delimiters
        self.assertIn("--- START OF FILE: file1.txt ---", aggregated_text)
        self.assertIn("This is file 1.", aggregated_text)
        self.assertIn("--- END OF FILE: file1.txt ---", aggregated_text)
        
        # Windows/Linux separators might differ in the path, but we are using os.path.normpath/glob
        # glob returns relative paths like sub/file2.txt
        path_sep_file2 = os.path.join("sub", "file2.txt")
        self.assertIn(f"--- START OF FILE: {path_sep_file2} ---", aggregated_text)
        self.assertIn("This is file 2.", aggregated_text)

    def test_exclude_directories(self):
        os.makedirs("venv")
        self.create_test_file("venv/hidden.txt", "hidden")
        aggregated_text, files = aggregate_text(["**/*"], no_copy=True)
        self.assertNotIn("venv/hidden.txt", files)
        self.assertNotIn("hidden", aggregated_text)

if __name__ == "__main__":
    unittest.main()