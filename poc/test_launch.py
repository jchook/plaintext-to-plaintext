"""Launcher preflight, model verification, and ownership checks."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import launch
import p2p


class LaunchTests(unittest.TestCase):
    def test_existing_model_is_hashed_and_not_downloaded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model'
            path.write_bytes(b'pinned model test')
            with patch.object(launch, 'model_path', return_value=path), \
                 patch.object(p2p, 'locate_server', return_value=Path('/runtime/llama-server')), \
                 patch.object(p2p, 'MODEL_SHA', hashlib.sha256(path.read_bytes()).hexdigest()), \
                 patch.object(launch.subprocess, 'run') as download:
                self.assertEqual(launch.prepare_model()[1], path)
                download.assert_not_called()
            with patch.object(launch, 'model_path', return_value=path), \
                 patch.object(p2p, 'locate_server', return_value=Path('/runtime/llama-server')):
                with self.assertRaisesRegex(p2p.CodecError, 'SHA-256'):
                    launch.prepare_model()

    def test_missing_runtime_prevents_model_download(self):
        with patch.object(p2p, 'locate_server', side_effect=p2p.CodecError('Missing runtime')), \
             patch.object(launch.subprocess, 'run') as download:
            with self.assertRaises(p2p.CodecError):
                launch.prepare_model()
            download.assert_not_called()

    def test_check_does_not_download_missing_model(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(launch, 'model_path', return_value=Path(folder) / 'missing'), \
             patch.object(p2p, 'locate_server', return_value=Path('/runtime/llama-server')), \
             patch.object(launch.subprocess, 'run') as download:
            with self.assertRaises(p2p.CodecError):
                launch.prepare_model(download=False)
            download.assert_not_called()

    def test_stop_only_acts_on_live_owned_children(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('child', 10), 0]
        launch.stop(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        stopped = Mock()
        stopped.poll.return_value = 0
        launch.stop(stopped)
        stopped.terminate.assert_not_called()
        vanished = Mock()
        vanished.poll.return_value = None
        vanished.terminate.side_effect = ProcessLookupError
        launch.stop(vanished)
        vanished.kill.assert_not_called()
        launch.stop(None)

    def test_startup_failure_and_timeout_are_reported(self):
        child = Mock()
        child.poll.return_value = 1
        with self.assertRaisesRegex(p2p.CodecError, 'exited'):
            launch.wait_ready('http://127.0.0.1:1', child, 1)
        child.poll.return_value = None
        with self.assertRaisesRegex(p2p.CodecError, 'timed out'):
            launch.wait_ready('http://127.0.0.1:1', child, 0)
