import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from core.upload_manager import UploadManager, UploadOptions, UploadState

class TestSmartSync(unittest.TestCase):
    def setUp(self):
        self.manager = UploadManager()
        self.manager._git = MagicMock()
        self.manager._emit_log = MagicMock()
        self.manager._emit_progress = MagicMock()
        
        # Mock successful init/add/commit
        self.manager._git.is_git_installed.return_value = True
        self.manager._git.is_repo.return_value = True
        self.manager._git.has_gitignore.return_value = True
        self.manager._git.add.return_value = True
        self.manager._git.commit.return_value = True
        self.manager._git.verify_push.return_value = True # sentinel check passes
        
        self.options = UploadOptions(
            folder_path=".",
            repo_full_name="test/repo",
            branch="main",
            force_push=False
        )

    def test_smart_sync_rebase_success(self):
        """Test Scenario: Push fails -> Rebase succeeds -> Push succeeds"""
        # First push fails
        # Rebase succeeds
        # Second push succeeds
        self.manager._git.push.side_effect = [False, True] 
        self.manager._git.rebase.return_value = True
        
        # Mock file system checks
        with patch('pathlib.Path.exists', return_value=True):
             self.manager._perform_upload(self.options)
        
        # Verify calls
        # 1. First push (failed)
        # 2. Rebase (called)
        # 3. Second push (success)
        self.assertEqual(self.manager._git.push.call_count, 2)
        self.manager._git.rebase.assert_called_once()
        self.manager._git.abort_rebase.assert_not_called()
        
        print("✅ Test 1 Passed: Smart Sync Rebase Success")

    def test_smart_sync_rebase_failure_fallback_force(self):
        """Test Scenario: Push fails -> Rebase fails -> Force Push succeeds"""
        # First push fails
        # Rebase fails
        # Force push succeeds
        self.manager._git.push.side_effect = [False, True] # First push fail, Second (Force) push success
        self.manager._git.rebase.return_value = False
        
        with patch('pathlib.Path.exists', return_value=True):
             self.manager._perform_upload(self.options)
             
        # Verify calls
        self.assertEqual(self.manager._git.push.call_count, 2)
        self.manager._git.rebase.assert_called_once()
        self.manager._git.abort_rebase.assert_called_once()
        
        # Verify second push was forced
        args, kwargs = self.manager._git.push.call_args_list[1]
        self.assertTrue(kwargs.get('force', False))
        
        print("✅ Test 2 Passed: Rebase Failure -> Force Push Fallback")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
