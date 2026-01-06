import os
import unittest
from text_aggregator.aggregator import aggregate_text
import tempfile
import shutil

class TestAggregator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.create_test_file("file1.txt", "This is file 1.")
        self.create_test_file("file2.txt", "This is file 2.")
        self.create_test_file("file3.log", "This is a log file.")
        self.create_test_file("file4.md", "This is a markdown file.")
        self.cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.test_dir)

    def create_test_file(self, filename, content):
        with open(os.path.join(self.test_dir, filename), "w") as f:
            f.write(content)

    def test_aggregate_all_text_files(self):
        expected_text = "This is file 1.\n\nThis is file 2."
        aggregated_text = aggregate_text("**/*.txt")
        self.assertEqual(aggregated_text.strip(), expected_text.strip())

    def test_aggregate_with_include_extensions(self):
        expected_text = "This is file 1.\n\nThis is file 2.\n\nThis is a markdown file."
        aggregated_text = aggregate_text("**/*", include_extensions=[ ".txt", ".md"])
        self.assertEqual(aggregated_text.strip(), expected_text.strip())

    def test_aggregate_with_exclude_extensions(self):
        expected_text = "This is file 1.\n\nThis is file 2.\n\nThis is a markdown file."
        aggregated_text = aggregate_text("**/*", exclude_extensions=[ ".log"])
        self.assertEqual(aggregated_text.strip(), expected_text.strip())

    def test_aggregate_to_file(self):
        output_file = "output.txt"
        self.assertIsNone(aggregate_text("**/*.txt", output_file=output_file))
        with open(output_file, "r") as f:
            content = f.read()
        expected_text = "This is file 1.\n\nThis is file 2."
        self.assertEqual(content.strip(), expected_text.strip())

    def test_aggregate_returns_text(self):
        expected_text = "This is file 1.\n\nThis is file 2."
        aggregated_text = aggregate_text("**/*.txt")
        self.assertEqual(aggregated_text.strip(), expected_text.strip())

if __name__ == "__main__":
    unittest.main()
