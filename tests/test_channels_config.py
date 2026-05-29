import unittest

from kai.content.channels import get_channel_config, reload_channel_config


class ChannelConfigTests(unittest.TestCase):
    def test_office_hours_weekday(self):
        reload_channel_config()
        ch = get_channel_config()
        self.assertIn(0, ch.office_weekdays)
        self.assertTrue(ch.is_live_agent_keyword("LA"))
        self.assertTrue(ch.is_resume_keyword("resume"))
        self.assertTrue(ch.is_blocked_media_type("image"))

    def test_resume_keyword_case_insensitive(self):
        ch = get_channel_config()
        self.assertTrue(ch.is_resume_keyword("Resume"))


if __name__ == "__main__":
    unittest.main()
