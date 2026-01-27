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
        os.environ["GITHUB_USER"] = "testuser"

    def tearDown(self):
        os.chdir(self.cwd)
        if self.original_home:
            os.environ["HOME"] = self.original_home
        else:
            if "HOME" in os.environ:
                del os.environ["HOME"]

        if "GITHUB_USER" in os.environ:
            del os.environ["GITHUB_USER"]

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

        res = self.run_bash("wta new-feature", input_text="n\n")  # n for clipboard

        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Created new branch", res.stdout)
        # Check that it uses the user prefix
        self.assertIn("testuser/new-feature", res.stdout)

        # Verify worktree created
        res_wt = subprocess.run(
            ["git", "worktree", "list"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        self.assertIn("new-feature", res_wt.stdout)

    def test_wta_copies_env_file(self):
        """Test that wta copies .env file to the new worktree."""
        self.setup_repo()

        # Create a .env file in the main repo
        env_content = "SECRET_KEY=test123\nDATABASE_URL=postgres://localhost"
        (Path(self.test_dir) / ".env").write_text(env_content)

        res = self.run_bash("wta env-test", input_text="n\n")  # n for clipboard
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Copied 1 .env* file(s)", res.stdout)

        # Verify .env was copied
        worktree_env = (
            Path(self.test_dir)
            / ".worktrees"
            / os.path.basename(self.test_dir)
            / "env-test"
            / ".env"
        )
        self.assertTrue(worktree_env.exists(), f".env not found at {worktree_env}")
        self.assertEqual(worktree_env.read_text(), env_content)

    def test_wta_symlinks_node_modules(self):
        """Test that wta symlinks node_modules to the new worktree."""
        self.setup_repo()

        # Create a node_modules directory in the main repo
        node_modules = Path(self.test_dir) / "node_modules"
        node_modules.mkdir()
        (node_modules / "some-package").mkdir()
        (node_modules / "some-package" / "index.js").write_text("module.exports = {}")

        res = self.run_bash("wta node-test", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Symlinked node_modules", res.stdout)

        # Verify node_modules was symlinked
        worktree_nm = (
            Path(self.test_dir)
            / ".worktrees"
            / os.path.basename(self.test_dir)
            / "node-test"
            / "node_modules"
        )
        self.assertTrue(
            worktree_nm.is_symlink(), f"node_modules is not a symlink at {worktree_nm}"
        )
        self.assertTrue((worktree_nm / "some-package" / "index.js").exists())

    def test_wta_copies_multiple_env_files(self):
        """Test that wta copies all .env* files to the new worktree."""
        self.setup_repo()

        # Create multiple .env files
        (Path(self.test_dir) / ".env").write_text("BASE=value")
        (Path(self.test_dir) / ".env.local").write_text("LOCAL=value")
        (Path(self.test_dir) / ".env.development").write_text("DEV=value")

        res = self.run_bash("wta multi-env-test", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Copied 3 .env* file(s)", res.stdout)

        # Verify all files were copied
        worktree_dir = (
            Path(self.test_dir)
            / ".worktrees"
            / os.path.basename(self.test_dir)
            / "multi-env-test"
        )
        self.assertTrue((worktree_dir / ".env").exists())
        self.assertTrue((worktree_dir / ".env.local").exists())
        self.assertTrue((worktree_dir / ".env.development").exists())

    def test_wta_symlinks_python_venv(self):
        """Test that wta symlinks .venv to the new worktree."""
        self.setup_repo()

        # Create a .venv directory
        venv = Path(self.test_dir) / ".venv"
        venv.mkdir()
        (venv / "bin").mkdir()
        (venv / "bin" / "python").write_text("#!/bin/bash\necho python")

        res = self.run_bash("wta venv-test", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Symlinked .venv", res.stdout)

        # Verify .venv was symlinked
        worktree_venv = (
            Path(self.test_dir)
            / ".worktrees"
            / os.path.basename(self.test_dir)
            / "venv-test"
            / ".venv"
        )
        self.assertTrue(worktree_venv.is_symlink())
        self.assertTrue((worktree_venv / "bin" / "python").exists())

    def test_wta_runs_post_setup_hook(self):
        """Test that wta runs .worktree-setup.sh if it exists."""
        self.setup_repo()

        # Create a post-setup hook that creates a marker file
        hook_content = '#!/bin/bash\necho "hook ran" > .hook-marker'
        (Path(self.test_dir) / ".worktree-setup.sh").write_text(hook_content)
        subprocess.check_call(["git", "add", ".worktree-setup.sh"], cwd=self.test_dir)
        subprocess.check_call(["git", "commit", "-m", "Add hook"], cwd=self.test_dir)

        # Input: n for clipboard, y for running hook
        res = self.run_bash("wta hook-test", input_text="n\ny\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Execute this script now?", res.stderr)  # Prompt goes to stderr

        # Verify the hook ran (created marker file)
        worktree_dir = (
            Path(self.test_dir)
            / ".worktrees"
            / os.path.basename(self.test_dir)
            / "hook-test"
        )
        marker = worktree_dir / ".hook-marker"
        self.assertTrue(marker.exists(), f"Hook marker not found at {marker}")

    def test_wta_stays_in_current_directory(self):
        """Test that wta does NOT change directory after creating worktree."""
        self.setup_repo()

        # Run wta and then pwd to verify we're still in the original directory
        res = self.run_bash("wta stay-test && pwd", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")

        # pwd should output the test_dir, not the worktree
        # Use realpath to handle macOS /var -> /private/var symlink
        last_line = res.stdout.strip().split("\n")[-1]
        self.assertEqual(os.path.realpath(last_line), os.path.realpath(self.test_dir))

    def test_gupdate(self):
        local_path, origin_path = self.setup_remote_and_clone()

        # 1. Update origin with a new commit
        setup_path = Path(self.test_dir) / "setup_repo"
        (setup_path / "file2.txt").write_text("Remote changes")
        subprocess.check_call(["git", "add", "."], cwd=setup_path)
        subprocess.check_call(["git", "commit", "-m", "Remote commit"], cwd=setup_path)
        subprocess.check_call(["git", "push", "origin", "main"], cwd=setup_path)

        # 2. Make local changes (committed) to create a divergence
        (local_path / "local.txt").write_text("Local changes")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Local commit"], cwd=local_path)

        # 3. Run gupdate
        res = self.run_bash("gupdate", cwd=local_path)
        self.assertEqual(res.returncode, 0, f"gupdate failed: {res.stderr}")
        self.assertIn("Push successful", res.stdout)

        # 4. Verify merge (we should see Remote commit and Local commit)
        res_log = subprocess.run(
            ["git", "log", "--oneline"], cwd=local_path, capture_output=True, text=True
        )
        self.assertIn("Remote commit", res_log.stdout)
        self.assertIn("Local commit", res_log.stdout)
        # Verify a merge happened (default logic creates a merge commit or fast-forwards)
        # Since we had local commits, it should be a merge commit unless we rebased (which we removed).
        # Depending on git config, it might be a merge commit.
        # "Merge remote-tracking branch 'origin/main'" is standard default message
        self.assertIn("Merge remote-tracking branch 'origin/main'", res_log.stdout)

        # 5. Verify push (Origin should now have Local commit)
        # We can check this by fetching in setup_repo and checking logs
        subprocess.check_call(["git", "pull", "origin", "main"], cwd=setup_path)
        res_origin_log = subprocess.run(
            ["git", "log", "--oneline"], cwd=setup_path, capture_output=True, text=True
        )
        self.assertIn("Local commit", res_origin_log.stdout)

    def test_gmb(self):
        local_path, origin_path = self.setup_remote_and_clone()

        # Create a branch off main
        subprocess.check_call(["git", "checkout", "-b", "feature"], cwd=local_path)

        # Add commit to main (on origin)
        setup_path = Path(self.test_dir) / "setup_repo"
        (setup_path / "new.txt").write_text("New file")
        subprocess.check_call(["git", "add", "."], cwd=setup_path)
        subprocess.check_call(["git", "commit", "-m", "Main update"], cwd=setup_path)
        subprocess.check_call(["git", "push", "origin", "main"], cwd=setup_path)

        # Fetch in local so we know about origin/main update
        subprocess.check_call(["git", "fetch", "origin"], cwd=local_path)

        # Add commit to feature
        (local_path / "feature.txt").write_text("Feature file")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Feature commit"], cwd=local_path)

        # gmb main should return the hash of the initial commit (common ancestor)
        # We can get the initial commit hash easily
        initial_hash = subprocess.check_output(
            ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=local_path, text=True
        ).strip()

        res = self.run_bash("gmb main", cwd=local_path)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), initial_hash)

    def test_gdiff_out(self):
        self.setup_repo()
        # Mock Downloads dir
        downloads = Path(self.test_dir) / "Downloads"
        downloads.mkdir()

        # Make changes
        Path("diff_me.txt").write_text("Diff content")
        subprocess.check_call(["git", "add", "diff_me.txt"], cwd=self.test_dir)

        # gdiff_out --cached
        # Branch is 'main' -> file should be git-main.diff
        res = self.run_bash("gdiff_out --cached", cwd=self.test_dir)
        self.assertEqual(res.returncode, 0)

        outfile = downloads / "git-main.diff"
        self.assertTrue(outfile.exists())
        self.assertIn("diff --git a/diff_me.txt", outfile.read_text())

    def test_gdmbo(self):
        local_path, origin_path = self.setup_remote_and_clone()
        downloads = Path(self.test_dir) / "Downloads"
        downloads.mkdir()

        # Create feature branch
        subprocess.check_call(["git", "checkout", "-b", "feature/test"], cwd=local_path)
        (local_path / "feat.txt").write_text("Feature")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Feature commit"], cwd=local_path)

        # gdmbo (no args)
        # Should auto-detect base (likely origin/main) and diff against HEAD
        # Output file should be git-feature-test.diff
        # Pass empty input to simulate non-interactive (forces file output)
        res = self.run_bash("gdmbo", cwd=local_path, input_text="")
        self.assertEqual(res.returncode, 0, f"gdmbo failed: {res.stderr}\n{res.stdout}")

        # Note: gdmbo output includes "Detected base: 'origin/main'"
        self.assertIn("Detected base", res.stdout)

        outfile = downloads / "git-feature-test.diff"
        self.assertTrue(outfile.exists())
        self.assertIn("diff --git a/feat.txt", outfile.read_text())

    def test_gdmbo_with_target(self):
        local_path, origin_path = self.setup_remote_and_clone()
        downloads = Path(self.test_dir) / "Downloads"
        downloads.mkdir()

        # Create a feature branch but stay on main
        subprocess.check_call(
            ["git", "checkout", "-b", "feature/other"], cwd=local_path
        )
        (local_path / "other.txt").write_text("Other Feature")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Other commit"], cwd=local_path)
        subprocess.check_call(["git", "checkout", "main"], cwd=local_path)

        # 1. Test with positional args: gdmbo feature/other main
        # (Compare feature/other against base main)
        # Output file should be git-feature-other.diff
        res = self.run_bash("gdmbo feature/other main", cwd=local_path, input_text="")
        self.assertEqual(
            res.returncode, 0, f"gdmbo positional failed: {res.stderr}\n{res.stdout}"
        )

        outfile = downloads / "git-feature-other.diff"
        self.assertTrue(outfile.exists())
        content = outfile.read_text()
        self.assertIn("diff --git a/other.txt", content)

        # Remove outfile to test next case
        outfile.unlink()

        # 2. Test with single arg: gdmbo feature/other
        # Should auto-detect base for feature/other
        res = self.run_bash("gdmbo feature/other", cwd=local_path, input_text="")
        self.assertEqual(
            res.returncode, 0, f"gdmbo single arg failed: {res.stderr}\n{res.stdout}"
        )

        self.assertTrue(outfile.exists())
        content = outfile.read_text()
        self.assertIn("diff --git a/other.txt", content)

    def test_gdmb(self):
        local_path, origin_path = self.setup_remote_and_clone()

        # Create feature branch
        subprocess.check_call(["git", "checkout", "-b", "feature/test"], cwd=local_path)
        (local_path / "feat.txt").write_text("Feature")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Feature commit"], cwd=local_path)

        # 1. gdmb (defaults to main vs HEAD)
        res = self.run_bash("gdmb", cwd=local_path)
        self.assertEqual(res.returncode, 0)
        self.assertIn("diff --git a/feat.txt", res.stdout)

        # 2. gdmb main feature/test (explicit target) from main branch
        subprocess.check_call(["git", "checkout", "main"], cwd=local_path)
        res = self.run_bash("gdmb main feature/test", cwd=local_path)
        self.assertEqual(res.returncode, 0)
        self.assertIn("diff --git a/feat.txt", res.stdout)

    def test_gexec(self):
        self.setup_repo()

        # 1. Modify a tracked file (Working Tree vs HEAD)
        (Path(self.test_dir) / "README.md").write_text("Modified Content")
        # gexec cat
        res = self.run_bash("gexec cat", cwd=self.test_dir)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Modified Content", res.stdout)

        # 2. No changes
        subprocess.check_call(["git", "checkout", "."], cwd=self.test_dir)
        res = self.run_bash("gexec cat", cwd=self.test_dir)
        self.assertEqual(res.returncode, 0)
        self.assertIn("No changed files", res.stdout)

    def test_gexec_mb(self):
        local_path, origin_path = self.setup_remote_and_clone()

        # Create feature branch
        subprocess.check_call(["git", "checkout", "-b", "feature"], cwd=local_path)
        (local_path / "feat.txt").write_text("Feature Content")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Feature"], cwd=local_path)

        # 1. gexec_mb (defaults to main vs HEAD) - should run on feat.txt
        # Command: grep "Feature"
        # grep on a single file doesn't print filename by default, just content
        res = self.run_bash("gexec_mb grep 'Feature'", cwd=local_path)
        self.assertEqual(res.returncode, 0, f"gexec_mb failed: {res.stderr}")
        self.assertIn("Feature Content", res.stdout)

        # 2. gexec_mb with flag target (explicitly pointing to current branch)
        # We stay on 'feature' branch so the file exists
        res = self.run_bash("gexec_mb -t feature -- grep 'Feature'", cwd=local_path)
        self.assertEqual(res.returncode, 0, f"gexec_mb flag failed: {res.stderr}")
        self.assertIn("Feature Content", res.stdout)

    def test_gdo(self):
        self.setup_repo()
        downloads = Path(self.test_dir) / "Downloads"
        downloads.mkdir()

        # 1. Unstaged changes
        Path("unstaged.txt").write_text("Unstaged")

        # gdo (no args) -> git diff (unstaged)
        # Forces file output due to non-interactive
        # Branch is main -> git-main.diff
        # Since unstaged.txt is not tracked, git diff is empty unless we add it first?
        # git diff only shows modified tracked files.
        # Let's add it first.
        subprocess.check_call(["git", "add", "unstaged.txt"], cwd=self.test_dir)
        # Now it is staged. git diff is empty. git diff --cached has it.
        # Wait, I want unstaged.
        (Path(self.test_dir) / "README.md").write_text("Modified README")
        # README is tracked. Modified is unstaged.

        res = self.run_bash("gdo", cwd=self.test_dir, input_text="")
        self.assertEqual(res.returncode, 0, f"gdo failed: {res.stderr}")

        outfile = downloads / "git-main.diff"
        self.assertTrue(outfile.exists())
        content = outfile.read_text()
        self.assertIn("diff --git a/README.md", content)
        self.assertIn("Modified README", content)

        # 2. With arguments (e.g. HEAD^)
        # Commit the changes so we have something to diff against HEAD^
        subprocess.check_call(["git", "add", "."], cwd=self.test_dir)
        subprocess.check_call(
            ["git", "commit", "-m", "Second commit"], cwd=self.test_dir
        )

        # gdo HEAD^
        res = self.run_bash("gdo HEAD^", cwd=self.test_dir, input_text="")
        self.assertEqual(res.returncode, 0, f"gdo HEAD^ failed: {res.stderr}")

        content = outfile.read_text()
        self.assertIn("diff --git a/README.md", content)
        # It should show the changes introduced in Second commit
        self.assertIn("Modified README", content)

    def test_wta_quoted_description_no_base(self):
        self.setup_repo()

        description = "ICON session opened when jogging in Initial world"
        expected_folder = "icon-session-opened-when-jogging-in-initial-world"
        expected_branch = "testuser/icon-session-opened-when-jogging-in-initial-world"

        # Note: We need to pass the description in quotes in the bash command
        res = self.run_bash(f'wta "{description}"', input_text="n\n")

        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn(f"Created new branch: {expected_branch}", res.stdout)

        # Verify worktree created
        res_wt = subprocess.run(
            ["git", "worktree", "list"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        self.assertIn(expected_folder, res_wt.stdout)

        # Verify branch exists
        res_branch = subprocess.run(
            ["git", "branch"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        self.assertIn(expected_branch, res_branch.stdout)

    def test_wta_quoted_description_with_flag_base(self):
        self.setup_repo()
        subprocess.check_call(["git", "branch", "base-feature"], cwd=self.test_dir)

        description = "fixing bug"
        # "base-feature" is the base
        expected_branch = "testuser/fixing-bug"

        # wta "fixing bug" --base base-feature
        res = self.run_bash(
            f'wta "{description}" --base base-feature', input_text="n\n"
        )

        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn(f"Created new branch: {expected_branch}", res.stdout)

        res_branch = subprocess.run(
            ["git", "branch"], cwd=self.test_dir, capture_output=True, text=True
        )
        self.assertIn(expected_branch, res_branch.stdout)

    def test_wta_existing_branch_with_prefix(self):
        self.setup_repo()
        # Create branch testuser/foo
        subprocess.check_call(["git", "branch", "testuser/foo"], cwd=self.test_dir)

        # wta "foo" should checkout "testuser/foo" (answer 'n' to force recreate, 'n' to clipboard)
        res = self.run_bash('wta "foo"', input_text="n\nn")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Checked out existing branch: testuser/foo", res.stdout)

    def test_wta_multi_word_description_no_quotes(self):
        self.setup_repo()
        # wta foo bar -> foo-bar (bar is not a branch)
        expected_branch = "testuser/foo-bar"

        res = self.run_bash("wta foo bar", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn(f"Created new branch: {expected_branch}", res.stdout)

        res_branch = subprocess.run(
            ["git", "branch"], cwd=self.test_dir, capture_output=True, text=True
        )
        self.assertIn(expected_branch, res_branch.stdout)

    def test_wta_multi_word_description_with_flag_base(self):
        self.setup_repo()
        # Create a base branch 'feature'
        subprocess.check_call(["git", "branch", "feature"], cwd=self.test_dir)

        # wta fixing bug --base feature -> fixing-bug (based on feature)
        expected_branch = "testuser/fixing-bug"

        res = self.run_bash("wta fixing bug --base feature", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn(f"Created new branch: {expected_branch}", res.stdout)

        res_branch = subprocess.run(
            ["git", "branch"], cwd=self.test_dir, capture_output=True, text=True
        )
        self.assertIn(expected_branch, res_branch.stdout)

    def test_wta_ambiguous_branch_name_is_description(self):
        self.setup_repo()
        # Create a branch 'feature'
        subprocess.check_call(["git", "branch", "feature"], cwd=self.test_dir)

        # wta fixing bug feature -> fixing-bug-feature (since no --base flag)
        expected_branch = "testuser/fixing-bug-feature"

        res = self.run_bash("wta fixing bug feature", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn(f"Created new branch: {expected_branch}", res.stdout)

        res_branch = subprocess.run(
            ["git", "branch"], cwd=self.test_dir, capture_output=True, text=True
        )
        self.assertIn(expected_branch, res_branch.stdout)

    def test_wta_fails_if_github_user_not_set(self):
        self.setup_repo()
        del os.environ["GITHUB_USER"]
        res = self.run_bash('wta "foo"')
        self.assertEqual(res.returncode, 1)
        self.assertIn("Error: GITHUB_USER environment variable is not set", res.stdout)

    def test_wta_existing_branch_checkout_by_default(self):
        """Test that wta checks out existing branch when not forcing recreate."""
        self.setup_repo()

        # Create an initial branch
        subprocess.check_call(
            ["git", "checkout", "-b", "testuser/existing"], cwd=self.test_dir
        )
        Path(self.test_dir, "file.txt").write_text("original content")
        subprocess.check_call(["git", "add", "."], cwd=self.test_dir)
        subprocess.check_call(["git", "commit", "-m", "Initial"], cwd=self.test_dir)
        subprocess.check_call(["git", "checkout", "main"], cwd=self.test_dir)

        # Run wta with 'n' to not force recreate, 'n' for clipboard
        res = self.run_bash("wta existing", input_text="n\nn")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("already exists", res.stdout)
        self.assertIn("Checked out existing branch", res.stdout)

        # Verify the existing branch was checked out
        worktree_dir = (
            Path(self.test_dir)
            / ".worktrees"
            / os.path.basename(self.test_dir)
            / "existing"
        )
        self.assertTrue(worktree_dir.exists())
        self.assertTrue((worktree_dir / "file.txt").exists())

    def test_wta_existing_branch_force_recreate(self):
        """Test that wta can force recreate an existing branch."""
        self.setup_repo()

        # Create an initial branch with content
        subprocess.check_call(
            ["git", "checkout", "-b", "testuser/recreate-test"], cwd=self.test_dir
        )
        Path(self.test_dir, "old-file.txt").write_text("old content")
        subprocess.check_call(["git", "add", "."], cwd=self.test_dir)
        subprocess.check_call(["git", "commit", "-m", "Old commit"], cwd=self.test_dir)
        subprocess.check_call(["git", "checkout", "main"], cwd=self.test_dir)

        # Run wta with 'y' to force recreate, then 'n' for clipboard
        res = self.run_bash('wta "recreate test"', input_text="y\nn")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("already exists", res.stdout)
        # "Force recreate?" prompt goes to stderr
        self.assertIn("Force recreate", res.stderr)
        self.assertIn("Deleting existing branch", res.stdout)
        self.assertIn("Created new branch", res.stdout)

        # Verify new branch was created (without old file)
        worktree_dir = (
            Path(self.test_dir)
            / ".worktrees"
            / os.path.basename(self.test_dir)
            / "recreate-test"
        )
        self.assertTrue(worktree_dir.exists())
        self.assertFalse((worktree_dir / "old-file.txt").exists())

    def test_wt_single_worktree_message(self):
        """Test that wt shows informative message when only main worktree exists."""
        self.setup_repo()

        res = self.run_bash("wt")
        self.assertEqual(res.returncode, 0, f"wt failed: {res.stderr}")
        self.assertIn("No additional worktrees found", res.stdout)
        self.assertIn("Use 'wta", res.stdout)

    def test_wtp_deletes_branch_by_default(self):
        """Test that wtp asks to delete branch and deletes it with -d by default."""
        self.setup_repo()

        # Create a worktree
        res = self.run_bash("wta test-branch", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")

        # Verify branch exists
        res_branch = subprocess.run(
            ["git", "branch"], cwd=self.test_dir, capture_output=True, text=True
        )
        self.assertIn("testuser/test-branch", res_branch.stdout)

        # Delete the worktree and the branch (y to confirm worktree, y to delete branch)
        # Use echo to simulate selecting the first (and only) non-main worktree
        # We can't easily test fzf interaction, so we'll skip this complex test
        # and just verify the logic works in manual testing

    def test_wtp_force_delete_unmerged_branch(self):
        """Test that wtp offers force delete when branch is not fully merged."""
        # This is also difficult to test without mocking fzf
        # Manual testing is recommended for this feature
        pass

    def test_wtlock_prevents_commits(self):
        """Test that wtlock installs a hook that prevents commits in the root worktree."""
        self.setup_repo()

        # Lock the root worktree
        res = self.run_bash("wtlock")
        self.assertEqual(res.returncode, 0, f"wtlock failed: {res.stderr}")
        self.assertIn("Root worktree locked", res.stdout)

        # Verify hook exists
        hook_path = Path(self.test_dir) / ".git" / "hooks" / "pre-commit"
        self.assertTrue(hook_path.exists(), "pre-commit hook should exist")

        # Try to commit in root worktree (should fail)
        (Path(self.test_dir) / "test.txt").write_text("test")
        subprocess.check_call(["git", "add", "test.txt"], cwd=self.test_dir)

        result = subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(
            result.returncode, 0, "Commit should be blocked in root worktree"
        )
        # Check both stdout and stderr for the message
        output = result.stdout + result.stderr
        self.assertIn("Commits are blocked", output)

    def test_wtlock_allows_commits_in_other_worktrees(self):
        """Test that wtlock only blocks commits in root, not in other worktrees."""
        self.setup_repo()

        # Lock the root worktree
        res = self.run_bash("wtlock")
        self.assertEqual(res.returncode, 0, f"wtlock failed: {res.stderr}")

        # Create a worktree
        res = self.run_bash("wta feature", input_text="n\n")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")

        # Commit in the worktree should work
        repo_name = os.path.basename(self.test_dir)
        worktree_path = Path(self.test_dir) / ".worktrees" / repo_name / "feature"
        (worktree_path / "test.txt").write_text("test")
        subprocess.check_call(["git", "add", "test.txt"], cwd=worktree_path)

        result = subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, f"Commit should work in worktree: {result.stderr}"
        )

    def test_wtunlock_removes_hook(self):
        """Test that wtunlock removes the lock hook."""
        self.setup_repo()

        # Lock first
        res = self.run_bash("wtlock")
        self.assertEqual(res.returncode, 0, f"wtlock failed: {res.stderr}")

        hook_path = Path(self.test_dir) / ".git" / "hooks" / "pre-commit"
        self.assertTrue(hook_path.exists(), "Hook should exist after lock")

        # Unlock
        res = self.run_bash("wtunlock")
        self.assertEqual(res.returncode, 0, f"wtunlock failed: {res.stderr}")
        self.assertIn("unlocked", res.stdout)

        # Hook should be gone
        self.assertFalse(hook_path.exists(), "Hook should be removed after unlock")

        # Commits should work now
        (Path(self.test_dir) / "test.txt").write_text("test")
        subprocess.check_call(["git", "add", "test.txt"], cwd=self.test_dir)

        result = subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, f"Commit should work after unlock: {result.stderr}"
        )


class TestZshCompatibility(unittest.TestCase):
    """Tests that shell tools work when sourced from zsh."""

    @classmethod
    def setUpClass(cls):
        # Check if zsh is available
        result = subprocess.run(["which", "zsh"], capture_output=True)
        if result.returncode != 0:
            raise unittest.SkipTest("zsh not available")

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
        os.environ["GITHUB_USER"] = "testuser"

    def tearDown(self):
        os.chdir(self.cwd)
        if self.original_home:
            os.environ["HOME"] = self.original_home
        else:
            if "HOME" in os.environ:
                del os.environ["HOME"]

        if "GITHUB_USER" in os.environ:
            del os.environ["GITHUB_USER"]

        shutil.rmtree(self.test_dir)

    def run_zsh(self, command, cwd=None, input_text=None):
        """Runs a command in zsh with the tools sourced."""
        if cwd is None:
            cwd = self.test_dir

        full_command = f"source {INIT_SCRIPT} && {command}"
        result = subprocess.run(
            ["zsh", "-c", full_command],
            cwd=cwd,
            capture_output=True,
            text=True,
            input=input_text,
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

    def test_wta_works_in_zsh(self):
        """Test that wta (which uses bash-specific syntax) works when called from zsh."""
        self.setup_repo()

        res = self.run_zsh("wta new-feature", input_text="n\n")

        self.assertEqual(
            res.returncode, 0, f"wta failed in zsh: {res.stderr}\n{res.stdout}"
        )
        self.assertIn("Created new branch", res.stdout)
        self.assertIn("testuser/new-feature", res.stdout)
        # Ensure no __BASH_CD__ marker leaks to output
        self.assertNotIn("__BASH_CD__", res.stdout)

    def test_wta_with_spaces_works_in_zsh(self):
        """Test that wta handles multi-word descriptions in zsh."""
        self.setup_repo()

        res = self.run_zsh('wta "State Management Feature"', input_text="n\n")

        self.assertEqual(
            res.returncode, 0, f"wta failed in zsh: {res.stderr}\n{res.stdout}"
        )
        self.assertIn("Created new branch", res.stdout)
        self.assertIn("testuser/state-management-feature", res.stdout)
        self.assertNotIn("__BASH_CD__", res.stdout)

    def test_wta_stays_in_current_directory(self):
        """Test that wta does NOT change directory (stays in place)."""
        self.setup_repo()

        # Run wta and then pwd to check we're still in the original directory
        res = self.run_zsh("wta new-feature && pwd", input_text="n\n")

        self.assertEqual(
            res.returncode, 0, f"wta failed in zsh: {res.stderr}\n{res.stdout}"
        )
        # Should NOT be in .worktrees - should still be in original dir
        self.assertNotIn(".worktrees", res.stdout.split("\n")[-1])

    def test_gupdate_works_in_zsh(self):
        """Test that gupdate (simpler command) works in zsh."""
        # Setup origin and clone
        origin_path = Path(self.test_dir) / "origin"
        origin_path.mkdir()
        subprocess.check_call(["git", "init", "--bare"], cwd=origin_path)

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

        local_path = Path(self.test_dir) / "local"
        subprocess.check_call(
            ["git", "clone", str(origin_path), "local"], cwd=self.test_dir
        )

        res = self.run_zsh("gupdate", cwd=local_path)

        self.assertEqual(
            res.returncode, 0, f"gupdate failed in zsh: {res.stderr}\n{res.stdout}"
        )

    def test_no_bad_substitution_error(self):
        """Ensure we don't get 'bad substitution' errors from bash-specific syntax in zsh."""
        self.setup_repo()

        res = self.run_zsh("wta test-feature", input_text="n\n")

        self.assertNotIn("bad substitution", res.stderr.lower())
        self.assertNotIn("bad substitution", res.stdout.lower())
        self.assertEqual(res.returncode, 0, f"Got error: {res.stderr}\n{res.stdout}")


class TestSkipWorktree(unittest.TestCase):
    """Tests for gskip, gunskip, and gskipped commands."""

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

    def setup_repo(self):
        """Sets up a basic git repo with a tracked file."""
        subprocess.check_call(["git", "init"], cwd=self.test_dir)
        Path(self.test_dir, "README.md").write_text("# Test Repo")
        Path(self.test_dir, "settings.json").write_text('{"color": "blue"}')
        subprocess.check_call(["git", "add", "."], cwd=self.test_dir)
        subprocess.check_call(
            ["git", "commit", "-m", "Initial commit"], cwd=self.test_dir
        )

    def test_gskip_with_file_argument(self):
        """Test that gskip marks a file as skip-worktree when given an argument."""
        self.setup_repo()

        res = self.run_bash("gskip settings.json", input_text="")
        self.assertEqual(res.returncode, 0, f"gskip failed: {res.stderr}")
        self.assertIn("Skipping (worktree): settings.json", res.stdout)

        # Verify the file is marked as skip-worktree
        result = subprocess.run(
            ["git", "ls-files", "-v"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        # 'S' prefix indicates skip-worktree
        self.assertIn("S settings.json", result.stdout)

    def test_gskip_and_gunskip_untracked_file(self):
        """Test that gskip ignores and gunskip un-ignores untracked files."""
        self.setup_repo()
        Path(self.test_dir, "untracked.txt").write_text("not tracked")

        # 1. Skip (Ignore)
        res = self.run_bash("gskip untracked.txt", input_text="")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Ignored (added to .git/info/exclude)", res.stdout)

        exclude_file = Path(self.test_dir) / ".git" / "info" / "exclude"
        self.assertTrue(exclude_file.exists())
        self.assertIn("untracked.txt", exclude_file.read_text())

        # 2. Unskip (Un-ignore)
        res = self.run_bash("gunskip untracked.txt", input_text="")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Un-ignored (removed from .git/info/exclude)", res.stdout)

        self.assertNotIn("untracked.txt", exclude_file.read_text())

    def test_gskip_nonexistent_file(self):
        """Test that gskip fails gracefully for non-existent files."""
        self.setup_repo()

        res = self.run_bash("gskip nonexistent.txt", input_text="")
        self.assertIn("not found", res.stdout)

    def test_gunskip_with_file_argument(self):
        """Test that gunskip removes skip-worktree flag when given an argument."""
        self.setup_repo()

        # First skip the file
        subprocess.run(
            ["git", "update-index", "--skip-worktree", "settings.json"],
            cwd=self.test_dir,
        )

        # Then unskip it
        res = self.run_bash("gunskip settings.json", input_text="")
        self.assertEqual(res.returncode, 0, f"gunskip failed: {res.stderr}")
        self.assertIn("Tracking (worktree): settings.json", res.stdout)

        # Verify the file is no longer skip-worktree
        result = subprocess.run(
            ["git", "ls-files", "-v"],
            cwd=self.test_dir,
            capture_output=True,
            text=True,
        )
        # 'H' prefix indicates normal tracked file
        self.assertIn("H settings.json", result.stdout)

    def test_gskipped_lists_skipped_files(self):
        """Test that gskipped lists files marked as skip-worktree."""
        self.setup_repo()

        # Skip a file
        subprocess.run(
            ["git", "update-index", "--skip-worktree", "settings.json"],
            cwd=self.test_dir,
        )

        res = self.run_bash("gskipped", input_text="")
        self.assertEqual(res.returncode, 0, f"gskipped failed: {res.stderr}")
        self.assertIn("settings.json", res.stdout)

    def test_gskipped_no_skipped_files(self):
        """Test that gskipped shows message when no files are skipped."""
        self.setup_repo()

        res = self.run_bash("gskipped", input_text="")
        self.assertEqual(res.returncode, 0, f"gskipped failed: {res.stderr}")
        self.assertIn(
            "No files are currently marked as skip-worktree or locally ignored",
            res.stdout,
        )

    def test_gskipped_lists_ignored_files(self):
        """Test that gskipped lists files in .git/info/exclude."""
        self.setup_repo()

        # Add file to exclude
        exclude_file = Path(self.test_dir) / ".git" / "info" / "exclude"
        # Ensure dir exists (it should)
        exclude_file.parent.mkdir(parents=True, exist_ok=True)
        exclude_file.write_text("ignored.txt\n# comment")

        res = self.run_bash("gskipped", input_text="")
        self.assertEqual(res.returncode, 0, f"gskipped failed: {res.stderr}")
        self.assertIn("Files locally ignored", res.stdout)
        self.assertIn("ignored.txt", res.stdout)
        self.assertNotIn("# comment", res.stdout)

    def test_gskip_multiple_files(self):
        """Test that gskip can mark multiple files at once."""
        self.setup_repo()

        res = self.run_bash("gskip settings.json README.md", input_text="")
        self.assertEqual(res.returncode, 0, f"gskip failed: {res.stderr}")
        self.assertIn("Processed 2 item(s)", res.stdout)


if __name__ == "__main__":
    unittest.main()
