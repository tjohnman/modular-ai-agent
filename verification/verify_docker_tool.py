import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from tools import python_analyser

class TestDockerToolHostPath(unittest.TestCase):
    @patch("docker.from_env")
    @patch("os.path.join")
    def test_execute_uses_host_workspace(self, mock_join, mock_docker_env):
        mock_client = MagicMock()
        mock_docker_env.return_value = mock_client
        mock_container = MagicMock()
        mock_client.containers.run.return_value = b"Output"
        
        # Setup mock paths
        workspace_dir = "/app/workspace"
        host_workspace_dir = os.path.join(project_root, "workspace")
        
        mock_join.return_value = "/app/workspace/_exec_script.py"
        
        # Execute tool with _host_workspace param
        params = {
            "code": "print('hello')",
            "_workspace": workspace_dir,
            "_host_workspace": host_workspace_dir
        }
        
        # We need to mock open since it writes to the file
        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            result = python_analyser.execute(params)
            
            # Verify containers.run was called with the HOST path in volumes
            mock_client.containers.run.assert_called_once()
            call_args = mock_client.containers.run.call_args
            volumes = call_args[1].get("volumes")
            
            self.assertIn(host_workspace_dir, volumes)
            self.assertEqual(volumes[host_workspace_dir]["bind"], "/workspace")
            self.assertEqual(volumes[host_workspace_dir]["mode"], "rw")

if __name__ == "__main__":
    unittest.main()
