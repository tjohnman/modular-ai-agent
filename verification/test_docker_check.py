import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import main (requires some mocking to avoid full startup)
with patch("dotenv.load_dotenv"), patch("utils.config.load_config"):
    import main

class TestDockerCheck(unittest.TestCase):

    @patch("docker.from_env")
    @patch("agent_system.utils.logger.info")
    def test_docker_check_success(self, mock_logger, mock_docker):
        # Setup mock client
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        # Should not raise or exit
        main.check_docker()
        
        mock_client.ping.assert_called_once()
        mock_logger.assert_called_with("Docker daemon is running.")

    @patch("docker.from_env")
    @patch("agent_system.utils.logger.error")
    @patch("sys.exit")
    def test_docker_check_failure(self, mock_exit, mock_logger, mock_docker):
        # Setup mock to raise error
        mock_docker.side_effect = Exception("Docker not running")
        
        main.check_docker()
        
        mock_exit.assert_called_once_with(1)
        # Check that error was logged
        self.assertTrue(any("Docker daemon is not running" in str(call) for call in mock_logger.call_args_list))

if __name__ == "__main__":
    unittest.main()
