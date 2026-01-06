import unittest
from unittest.mock import MagicMock, patch, call
import os
import time
from command_reloader.reloader import CommandReloader


class TestCommandReloader(unittest.TestCase):

    @patch("subprocess.Popen")
    @patch("subprocess.check_output")
    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_snapshot_parsing(
        self, mock_mtime, mock_exists, mock_check_output, mock_popen
    ):
        reloader = CommandReloader("echo test")

        # Mock git status output
        # M file1.txt
        # ?? newfile.txt
        mock_check_output.return_value = b" M file1.txt\x00?? newfile.txt\x00"

        mock_exists.return_value = True
        mock_mtime.side_effect = lambda path: 100.0 if path == "file1.txt" else 200.0

        snapshot = reloader._get_snapshot()

        self.assertEqual(snapshot["file1.txt"], 100.0)
        self.assertEqual(snapshot["newfile.txt"], 200.0)

    @patch("subprocess.Popen")
    @patch("subprocess.check_output")
    def test_start_process_standard(self, mock_check_output, mock_popen):
        """Test standard startup (no regex)."""
        reloader = CommandReloader("my_command")
        reloader._start_main_process()

        mock_popen.assert_called_with("my_command", shell=True, preexec_fn=os.setsid)
        self.assertIsNotNone(reloader.process)

    @patch("pty.openpty")
    @patch("os.close")
    @patch("threading.Thread")
    @patch("subprocess.Popen")
    @patch("subprocess.check_output")
    def test_start_process_regex(
        self, mock_check_output, mock_popen, mock_thread, mock_close, mock_openpty
    ):
        """Test startup with regex (uses pty)."""
        reloader = CommandReloader("my_command", wait_for_regex="Started")
        mock_openpty.return_value = (10, 11)  # Master, Slave

        reloader._start_main_process()

        mock_popen.assert_called_with(
            "my_command",
            shell=True,
            stdout=11,
            stderr=11,
            stdin=11,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        # Should close slave fd
        mock_close.assert_called_with(11)
        # Should start monitor thread
        mock_thread.assert_called_once()
        self.assertEqual(reloader.master_fd, 10)

    @patch("os.killpg")
    @patch("os.getpgid")
    @patch("subprocess.Popen")
    def test_stop_process(self, mock_popen, mock_getpgid, mock_killpg):
        reloader = CommandReloader("cmd")
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        reloader._start_main_process()
        reloader.stop_process()

        mock_getpgid.assert_called_with(12345)
        mock_killpg.assert_called()
        mock_process.wait.assert_called()
        self.assertIsNone(reloader.process)

    @patch("subprocess.check_output")
    def test_git_root_check(self, mock_check_output):
        reloader = CommandReloader("cmd")
        mock_check_output.return_value = b"/path/to/repo\n"

        root = reloader._get_git_root()
        self.assertEqual(root, "/path/to/repo")
        mock_check_output.assert_called_with(
            ["git", "rev-parse", "--show-toplevel"], stderr=-3
        )

    def test_debounce_init(self):
        reloader = CommandReloader("cmd", debounce_interval=2.5)
        self.assertEqual(reloader.debounce_interval, 2.5)


if __name__ == "__main__":
    unittest.main()
