import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

# Path to the init script
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INIT_SCRIPT = REPO_ROOT / "shell_commands" / "init.sh"


class TestShellTools(unittest.TestCase):
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
        subprocess.check_call(["git", "config", "--global", "user.name", "Your Name"])
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

    def run_bash(self, command, cwd=None):
        """Runs a bash command with the tools sourced."""
        if cwd is None:
            cwd = self.test_dir

        full_command = f"source {INIT_SCRIPT} && {command}"
        result = subprocess.run(
            ["bash", "-c", full_command], cwd=cwd, capture_output=True, text=True
        )
        return result

    def setup_repo(self):
        """Sets up a basic git repo."""
        subprocess.check_call(["git", "init"], cwd=self.test_dir)
        Path("README.md").write_text("# Test Repo")
        subprocess.check_call(["git", "add", "."], cwd=self.test_dir)
        subprocess.check_call(
            ["git", "commit", "-m", "Initial commit"], cwd=self.test_dir
        )

    def setup_remote_and_clone(self):
        """Sets up an 'origin' repo and a local clone."""
        origin_path = Path(self.test_dir) / "origin"
        origin_path.mkdir()
        subprocess.check_call(["git", "init", "--bare"], cwd=origin_path)

        # Create a temp repo to push initial commit to origin
        setup_path = Path(self.test_dir) / "setup_repo"
        setup_path.mkdir()
        subprocess.check_call(["git", "init"], cwd=setup_path)
        (setup_path / "README.md").write_text("# Origin")
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

        return local_path, origin_path

    def test_glog(self):
        self.setup_repo()
        res = self.run_bash("glog")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Initial commit", res.stdout)

    def test_gst(self):
        self.setup_repo()
        Path("newfile.txt").touch()
        res = self.run_bash("gst")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Untracked files", res.stdout)

    def test_wta_create_new_branch(self):
        self.setup_repo()
        # wta uses $HOME to determine where to put worktrees (~/.worktrees).
        # We have mocked HOME to be self.test_dir in setUp.

        res = self.run_bash("wta new-feature")

        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Created new branch", res.stdout)

        # Verify worktree created
        res_wt = subprocess.run(
            ["git", "worktree", "list"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        self.assertIn("new-feature", res_wt.stdout)

    def test_gupdate(self):
        local_path, origin_path = self.setup_remote_and_clone()

        # 1. Update origin with a new commit
        setup_path = Path(self.test_dir) / "setup_repo"
        (setup_path / "file2.txt").write_text("Remote changes")
        subprocess.check_call(["git", "add", "."], cwd=setup_path)
        subprocess.check_call(["git", "commit", "-m", "Remote commit"], cwd=setup_path)
        subprocess.check_call(["git", "push", "origin", "main"], cwd=setup_path)

        # 2. Make local changes (staged)
        (local_path / "local.txt").write_text("Local changes")
        subprocess.check_call(["git", "add", "."], cwd=local_path)

        # 3. Run gupdate
        res = self.run_bash("gupdate", cwd=local_path)
        self.assertEqual(res.returncode, 0, f"gupdate failed: {res.stderr}")

        # 4. Verify rebase (we should see Remote commit)
        res_log = subprocess.run(
            ["git", "log", "--oneline"], cwd=local_path, capture_output=True, text=True
        )
        self.assertIn("Remote commit", res_log.stdout)

        # 5. Verify stash popped (local.txt should be there and staged)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=local_path,
            capture_output=True,
            text=True,
        )
        self.assertIn("A  local.txt", status.stdout)

    def test_grestack(self):
        local_path, origin_path = self.setup_remote_and_clone()

        # Setup stack: main -> parent -> child

        # Create parent branch and push
        subprocess.check_call(["git", "checkout", "-b", "parent"], cwd=local_path)
        (local_path / "parent.txt").write_text("Parent content")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Parent commit"], cwd=local_path)
        subprocess.check_call(["git", "push", "-u", "origin", "parent"], cwd=local_path)

        # Create child branch
        subprocess.check_call(["git", "checkout", "-b", "child"], cwd=local_path)
        (local_path / "child.txt").write_text("Child content")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Child commit"], cwd=local_path)

        # Squash merge parent into main (on origin)
        # We simulate this by checking out main, checking out parent files, committing.
        setup_path = Path(self.test_dir) / "setup_repo"
        subprocess.check_call(["git", "checkout", "main"], cwd=setup_path)
        (setup_path / "parent.txt").write_text("Parent content")
        subprocess.check_call(["git", "add", "."], cwd=setup_path)
        subprocess.check_call(
            ["git", "commit", "-m", "Squashed parent"], cwd=setup_path
        )
        subprocess.check_call(["git", "push", "origin", "main"], cwd=setup_path)

        # Now back to local. 'child' is based on 'parent' (old hash).
        # main has 'Squashed parent' (new hash).
        # grestack parent main should rebase child onto main, dropping parent commit.

        res = self.run_bash("grestack parent origin/main", cwd=local_path)
        self.assertEqual(res.returncode, 0, f"grestack failed: {res.stderr}")

        # Verify history: Should have Child commit and Squashed parent. Should NOT have old Parent commit.
        log = subprocess.run(
            ["git", "log", "--oneline"], cwd=local_path, capture_output=True, text=True
        )
        self.assertIn("Child commit", log.stdout)
        self.assertIn("Squashed parent", log.stdout)
        # Since we squashed, the message "Parent commit" shouldn't be there (unless we check message, but hashes differ)
        # However, git log output is just strings. "Parent commit" was the message of the old commit.
        # "Squashed parent" is the new one.
        self.assertNotIn("Parent commit", log.stdout)


if __name__ == "__main__":
    unittest.main()
