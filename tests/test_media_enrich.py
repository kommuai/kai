"""Inbound media enrichment (voice STT, future vision)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kai.content.channels import get_channel_config, reload_channel_config
from kai.media.config import get_media_config, reload_media_config
from kai.media.enrich import enrich_inbound_media
from kai.media.stt import SttResult


class MediaConfigTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "minimal_workspace"
        os.environ["KAI_HOME"] = str(fixture)
        self._clear_caches()

    def tearDown(self):
        os.environ.pop("KAI_HOME", None)
        self._clear_caches()

    def _clear_caches(self):
        for fn in (
            "kai.settings.get_settings",
            "kai.workspace.manifest.load_workspace_data",
            "kai.workspace.manifest._load_workspace_manifest_cached",
            "kai.media.config.get_media_config",
            "kai.content.channels.get_channel_config",
        ):
            try:
                mod_name, func_name = fn.rsplit(".", 1)
                import importlib

                mod = importlib.import_module(mod_name)
                getattr(mod, func_name).cache_clear()
            except Exception:
                pass
        reload_media_config()
        reload_channel_config()

    def test_voice_not_blocked_when_stt_enabled(self):
        ch = get_channel_config()
        cfg = get_media_config()
        self.assertTrue(cfg.stt_enabled)
        self.assertFalse(ch.is_blocked_media_type("voice"))
        self.assertFalse(ch.is_blocked_media_type("audio"))
        self.assertTrue(ch.is_blocked_media_type("image"))

    def test_image_still_blocked(self):
        ch = get_channel_config()
        self.assertTrue(ch.is_blocked_media_type("image"))


class EnrichVoiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._home = Path(self._tmp)
        (self._home / "data").mkdir()
        (self._home / "workspace.yaml").write_text(
            "version: '2'\n"
            "tenant:\n  id: test\n  display_name: Test\n  default_lang: en\n  timezone: UTC\n"
            "session_store:\n  path: data/sessions.db\n"
            "channels:\n  media:\n    blocked_types: [image, video]\n"
            "    storage_dir: data/media\n"
            "    stt:\n      enabled: true\n      min_confidence: 0.5\n"
            "    enrich:\n      voice_template_en: '[Voice]: {transcript}'\n",
            encoding="utf-8",
        )
        os.environ["KAI_HOME"] = str(self._home)
        self._audio = self._home / "sample.ogg"
        self._audio.write_bytes(b"fake-audio")
        self._clear_caches()

    def tearDown(self):
        os.environ.pop("KAI_HOME", None)
        self._clear_caches()

    def _clear_caches(self):
        reload_media_config()
        reload_channel_config()
        try:
            from kai.settings import get_settings

            get_settings.cache_clear()
        except Exception:
            pass
        try:
            from kai.workspace.manifest import load_workspace_data

            load_workspace_data.cache_clear()
        except Exception:
            pass

    @patch("kai.media.enrich.transcribe_audio")
    def test_enrich_voice_success(self, mock_stt):
        mock_stt.return_value = SttResult(transcript="My dashcam won't connect", confidence=0.92)
        enriched = enrich_inbound_media(
            {
                "modality": "voice",
                "path": str(self._audio),
                "msg_id": "msg-1",
                "mimetype": "audio/ogg",
            },
            lang="EN",
        )
        self.assertFalse(enriched.skipped_runtime)
        self.assertIn("My dashcam won't connect", enriched.text)
        self.assertTrue(Path(enriched.stored_path).is_file())

    @patch("kai.media.enrich.transcribe_audio")
    def test_enrich_voice_low_confidence_fallback(self, mock_stt):
        mock_stt.return_value = SttResult(transcript="mumble", confidence=0.2)
        enriched = enrich_inbound_media(
            {
                "modality": "voice",
                "path": str(self._audio),
                "msg_id": "msg-2",
            },
            lang="EN",
        )
        self.assertTrue(enriched.skipped_runtime)
        self.assertEqual(enriched.decision, "stt_low_confidence")

    def test_image_raises_when_vision_disabled(self):
        with self.assertRaises(ValueError):
            enrich_inbound_media(
                {
                    "modality": "image",
                    "path": str(self._audio),
                    "msg_id": "img-1",
                },
                lang="EN",
            )


if __name__ == "__main__":
    unittest.main()
