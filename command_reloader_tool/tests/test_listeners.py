import unittest
from unittest.mock import MagicMock, patch
import http.server
import sys
import os

# Import the listener modules
# We need to add the parent directory to sys.path to import from listeners
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from listeners import mac_listener, linux_listener

class TestMacListener(unittest.TestCase):
    def test_get_applescript(self):
        script = mac_listener.get_applescript(3000)
        self.assertIn(':3000', script) # check basic interpolation
        self.assertIn('reload t', script)

    @patch('subprocess.Popen')
    def test_handler_triggers_process(self, mock_popen):
        # Setup mock process
        process_mock = MagicMock()
        process_mock.communicate.return_value = (b"", b"")
        process_mock.return_value = 0
        mock_popen.return_value = process_mock

        # Setup handler
        server = MagicMock()
        server.app_port = 8080
        
        # We patch BaseHTTPRequestHandler init to do nothing, 
        # AND we need to mock send_response/end_headers since we didn't init the base class properly
        with patch('http.server.BaseHTTPRequestHandler.__init__', return_value=None):
            handler = mac_listener.Handler(MagicMock(), MagicMock(), server)
            handler.server = server
            handler.wfile = MagicMock()
            handler.send_response = MagicMock()
            handler.end_headers = MagicMock()
            
            handler.do_GET()
            
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            self.assertEqual(args[0], ['osascript', '-'])
            self.assertIn('stdin', kwargs)

class TestLinuxListener(unittest.TestCase):
    def test_refresh_window_command(self):
        cmd = linux_listener.refresh_window(8080)
        self.assertIn("xdotool search", cmd)
        self.assertIn("key F5", cmd)

    @patch('subprocess.run')
    def test_handler_triggers_process(self, mock_run):
        server = MagicMock()
        server.app_port = 8080
        
        with patch('http.server.BaseHTTPRequestHandler.__init__', return_value=None):
            handler = linux_listener.Handler(MagicMock(), MagicMock(), server)
            handler.server = server
            handler.wfile = MagicMock()
            handler.send_response = MagicMock()
            handler.end_headers = MagicMock()
            
            handler.do_GET()
            
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            self.assertIn("xdotool", args[0])

if __name__ == '__main__':
    unittest.main()