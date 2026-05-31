"""STT provider routing."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from kai.media.stt import SttResult, transcribe_audio


class SttProviderTests(unittest.TestCase):
    @patch("kai.media.stt.get_media_config")
    @patch("kai.media.stt._server_health_ok", return_value=False)
    @patch("kai.media.stt_local.transcribe_local")
    def test_faster_whisper_uses_local_when_no_server(self, mock_local, _health, mock_cfg):
        mock_cfg.return_value.stt_provider = "faster_whisper"
        mock_local.return_value = SttResult(transcript="hello", confidence=0.9)
        result = transcribe_audio(Path("/tmp/x.ogg"))
        self.assertEqual(result.transcript, "hello")
        mock_local.assert_called_once()

    @patch("kai.media.stt.get_media_config")
    @patch("kai.media.stt._server_health_ok", return_value=True)
    @patch("kai.media.stt._transcribe_via_server")
    def test_faster_whisper_uses_sidecar_when_healthy(self, mock_server, _health, mock_cfg):
        mock_cfg.return_value.stt_provider = "faster_whisper"
        mock_server.return_value = SttResult(transcript="from sidecar", confidence=0.88)
        result = transcribe_audio(Path("/tmp/x.ogg"))
        self.assertEqual(result.transcript, "from sidecar")


if __name__ == "__main__":
    unittest.main()
