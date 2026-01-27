import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

# Path to the init script
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INIT_SCRIPT = REPO_ROOT / "shell_commands" / "init.sh"


class TestDiffContext(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.test_dir

        # Configure git for testing
        subprocess.check_call(
            ["git", "config", "--global", "user.email", "you@example.com"]
        )
        subprocess.check_call(["git", "config", "--global", "user.name", "Your Name"]
        )
        subprocess.check_call(
            ["git", "config", "--global", "init.defaultBranch", "main"]
        )

    def tearDown(self):
        os.chdir(self.cwd)
        if self.original_home:
            os.environ["HOME"] = self.original_home
        else:
            if "HOME" in os.environ:
                del os.environ["HOME"]
        shutil.rmtree(self.test_dir)

    def run_bash(self, command, cwd=None, input_text=None):
        """Runs a bash command with the tools sourced."""
        if cwd is None:
            cwd = self.test_dir

        full_command = f"source {INIT_SCRIPT} && {command}"
        result = subprocess.run(
            ["bash", "-c", full_command],
            cwd=cwd,
            capture_output=True,
            text=True,
            input=input_text,
        )
        return result

    def setup_repo_with_large_file(self):
        """Sets up a repo with a file containing 100 lines."""
        subprocess.check_call(["git", "init"], cwd=self.test_dir)
        
        # Create a file with 100 lines
        lines = [f"Line {i}" for i in range(1, 101)]
        Path(self.test_dir, "large_file.txt").write_text("\n".join(lines))
        
        subprocess.check_call(["git", "add", "."], cwd=self.test_dir)
        subprocess.check_call(
            ["git", "commit", "-m", "Initial commit"], cwd=self.test_dir
        )
        return lines

    def setup_remote_and_clone_with_large_file(self):
        """Sets up an 'origin' repo with a large file and a local clone."""
        origin_path = Path(self.test_dir) / "origin"
        origin_path.mkdir()
        subprocess.check_call(["git", "init", "--bare"], cwd=origin_path)

        # Create a temp repo to push initial commit to origin
        setup_path = Path(self.test_dir) / "setup_repo"
        setup_path.mkdir()
        subprocess.check_call(["git", "init"], cwd=setup_path)
        
        lines = [f"Line {i}" for i in range(1, 101)]
        (setup_path / "large_file.txt").write_text("\n".join(lines))
        
        subprocess.check_call(["git", "add", "."], cwd=setup_path)
        subprocess.check_call(["git", "commit", "-m", "Initial"], cwd=setup_path)
        subprocess.check_call(
            ["git", "remote", "add", "origin", str(origin_path)], cwd=setup_path
        )
        subprocess.check_call(["git", "push", "-u", "origin", "main"], cwd=setup_path)

        # Clone it
        local_path = Path(self.test_dir) / "local"
        subprocess.check_call(
            ["git", "clone", str(origin_path), "local"], cwd=self.test_dir
        )

        return local_path, lines

    def test_gdo_full_context(self):
        """Test that gdo shows full context (more than 3 lines)."""
        lines = self.setup_repo_with_large_file()
        
        # Mock Downloads dir
        downloads = Path(self.test_dir) / "Downloads"
        downloads.mkdir()

        # Modify line 50
        lines[49] = "Line 50 Modified"
        Path(self.test_dir, "large_file.txt").write_text("\n".join(lines))

        # Run gdo
        # Use empty input to force file output (since we are not interactive)
        res = self.run_bash("gdo", cwd=self.test_dir, input_text="")
        self.assertEqual(res.returncode, 0, f"gdo failed: {res.stderr}")

        outfile = downloads / "git-main.diff"
        self.assertTrue(outfile.exists())
        content = outfile.read_text()
        
        # Check for diff header
        self.assertIn("diff --git a/large_file.txt", content)
        
        # Check for the change
        self.assertIn("+Line 50 Modified", content)
        
        # Check for context far away (e.g., Line 1, Line 100)
        # Default git diff shows only 3 lines of context.
        # With -U9999, it should show everything.
        self.assertIn("Line 1", content)
        self.assertIn("Line 10", content) 
        self.assertIn("Line 90", content)
        self.assertIn("Line 100", content)

    def test_gdmbo_full_context(self):
        """Test that gdmbo shows full context."""
        local_path, lines = self.setup_remote_and_clone_with_large_file()
        downloads = Path(self.test_dir) / "Downloads"
        downloads.mkdir()
        
        # Create a feature branch
        subprocess.check_call(["git", "checkout", "-b", "feature"], cwd=local_path)
        
        # Modify line 50
        lines[49] = "Line 50 Modified"
        (local_path / "large_file.txt").write_text("\n".join(lines))
        
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Modify line 50"], cwd=local_path)

        # Run gdmbo main
        res = self.run_bash("gdmbo main", cwd=local_path, input_text="")
        self.assertEqual(res.returncode, 0, f"gdmbo failed: {res.stderr}")

        outfile = downloads / "git-feature.diff"
        self.assertTrue(outfile.exists())
        content = outfile.read_text()
        
        # Check for the change
        self.assertIn("+Line 50 Modified", content)
        
        # Check for context
        self.assertIn("Line 1", content)
        self.assertIn("Line 100", content)

if __name__ == "__main__":
    unittest.main()
