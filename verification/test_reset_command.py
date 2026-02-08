import os
import sys
import shutil
from unittest.mock import MagicMock, patch

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from agent_system.core.engine import Engine

@patch("os.listdir")
@patch("os.path.isfile")
@patch("os.path.isdir")
@patch("os.unlink")
@patch("shutil.rmtree")
@patch("os.path.exists")
@patch("os.makedirs")
def test_reset_command(mock_makedirs, mock_exists, mock_rmtree, mock_unlink, mock_isdir, mock_isfile, mock_listdir):
    provider = MagicMock()
    channel = MagicMock()
    persistence = MagicMock()
    
    # Setup mocks
    def exists_side_effect(path):
        # Return False for the output dir to verify it gets recreated
        if path.endswith("output"):
            return False
        return True
    mock_exists.side_effect = exists_side_effect
    
    mock_listdir.return_value = ["file1.txt", "dir1"]
    
    def is_file_side_effect(path):
        return "file1.txt" in path
    def is_dir_side_effect(path):
        return "dir1" in path
        
    mock_isfile.side_effect = is_file_side_effect
    mock_isdir.side_effect = is_dir_side_effect
    
    # Mock Engine initialization methods
    with patch.object(Engine, "_load_system_prompt", return_value="System Prompt"):
        with patch.object(Engine, "load_tools"):
            engine = Engine(provider=provider, channels=[channel], persistence=persistence, workspace_dir="test_workspace")
            # Override current_channel which is set in run() usually but we can set it here for test
            engine.current_channel = channel

            print("Testing /reset command execution...")
            engine._handle_reset()
            
            # Verify persistence.start_new_session was called
            persistence.start_new_session.assert_called_once()
            print("✓ persistence.start_new_session called.")
            
            abs_workspace = os.path.abspath("test_workspace")
            
            # Verify os.unlink was called for the file
            mock_unlink.assert_called_with(os.path.join(abs_workspace, "file1.txt"))
            print("✓ os.unlink called for file1.txt.")
            
            # Verify shutil.rmtree was called for the directory
            mock_rmtree.assert_called_with(os.path.join(abs_workspace, "dir1"))
            print("✓ shutil.rmtree called for dir1.")
            
            # Verify _ensure_dirs was called (indirectly via mock_makedirs)
            # _ensure_dirs creates workspace_dir, tools_dir, and workspace/output
            assert mock_makedirs.call_count >= 1
            print("✓ Workspace structure re-ensured.")
            
            # Verify message sent to channel
            channel.send_output.assert_called_with("Session reset. Conversation history cleared and workspace emptied.")
            print("✓ Confirmation message sent to channel.")

if __name__ == "__main__":
    try:
        test_reset_command()
        print("\nALL RESET TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
