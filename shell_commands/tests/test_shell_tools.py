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
        
        res = self.run_bash("wta env-test")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Copied .env", res.stdout)
        
        # Verify .env was copied
        worktree_env = Path(self.test_dir) / ".worktrees" / os.path.basename(self.test_dir) / "env-test" / ".env"
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
        
        res = self.run_bash("wta node-test")
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Symlinked node_modules", res.stdout)
        
        # Verify node_modules was symlinked
        worktree_nm = Path(self.test_dir) / ".worktrees" / os.path.basename(self.test_dir) / "node-test" / "node_modules"
        self.assertTrue(worktree_nm.is_symlink(), f"node_modules is not a symlink at {worktree_nm}")
        self.assertTrue((worktree_nm / "some-package" / "index.js").exists())

    def test_wta_stays_in_current_directory(self):
        """Test that wta does NOT change directory after creating worktree."""
        self.setup_repo()
        
        # Run wta and then pwd to verify we're still in the original directory
        res = self.run_bash("wta stay-test && pwd")
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

    def test_gdmb(self):
        local_path, origin_path = self.setup_remote_and_clone()
        downloads = Path(self.test_dir) / "Downloads"
        downloads.mkdir()

        # Create feature branch
        subprocess.check_call(["git", "checkout", "-b", "feature/test"], cwd=local_path)
        (local_path / "feat.txt").write_text("Feature")
        subprocess.check_call(["git", "add", "."], cwd=local_path)
        subprocess.check_call(["git", "commit", "-m", "Feature commit"], cwd=local_path)

        # gdmb main
        # Should diff against origin/main (which is the parent)
        # Output file should be git-feature-test.diff
        res = self.run_bash("gdmb main", cwd=local_path)
        self.assertEqual(res.returncode, 0, f"gdmb failed: {res.stderr}")

        outfile = downloads / "git-feature-test.diff"
        self.assertTrue(outfile.exists())
        self.assertIn("diff --git a/feat.txt", outfile.read_text())

    def test_wta_quoted_description_no_base(self):
        self.setup_repo()

        description = "ICON session opened when jogging in Initial world"
        expected_folder = "icon-session-opened-when-jogging-in-initial-world"
        expected_branch = "testuser/icon-session-opened-when-jogging-in-initial-world"

        # Note: We need to pass the description in quotes in the bash command
        res = self.run_bash(f'wta "{description}"')

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
        res = self.run_bash(f'wta "{description}" --base base-feature')

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

        # wta "foo" should checkout "testuser/foo"
        res = self.run_bash('wta "foo"')
        self.assertEqual(res.returncode, 0, f"wta failed: {res.stderr}")
        self.assertIn("Checked out existing branch: testuser/foo", res.stdout)

    def test_wta_multi_word_description_no_quotes(self):
        self.setup_repo()
        # wta foo bar -> foo-bar (bar is not a branch)
        expected_branch = "testuser/foo-bar"

        res = self.run_bash("wta foo bar")
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

        res = self.run_bash("wta fixing bug --base feature")
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

        res = self.run_bash("wta fixing bug feature")
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

    def run_zsh(self, command, cwd=None):
        """Runs a zsh command with the tools sourced."""
        if cwd is None:
            cwd = self.test_dir

        full_command = f"source {INIT_SCRIPT} && {command}"
        result = subprocess.run(
            ["zsh", "-c", full_command], cwd=cwd, capture_output=True, text=True
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

        res = self.run_zsh("wta new-feature")

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

        res = self.run_zsh('wta "State Management Feature"')

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
        res = self.run_zsh("wta new-feature && pwd")

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

        res = self.run_zsh("wta test-feature")

        self.assertNotIn("bad substitution", res.stderr.lower())
        self.assertNotIn("bad substitution", res.stdout.lower())
        self.assertEqual(res.returncode, 0, f"Got error: {res.stderr}\n{res.stdout}")


if __name__ == "__main__":
    unittest.main()
