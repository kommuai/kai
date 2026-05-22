"""WhatsApp length cap used on all user-visible replies."""

import unittest

from kai.core.outbound_delivery import WHATSAPP_MAX_BODY, prepare_outbound_reply


class OutboundDeliveryTests(unittest.TestCase):
    def test_short_message_unchanged(self):
        msg, meta = prepare_outbound_reply("Hello", "EN")
        self.assertEqual(msg, "Hello")
        self.assertFalse(meta.get("truncated"))

    def test_long_install_message_truncated(self):
        body = "install " + ("step " * 2000)
        msg, meta = prepare_outbound_reply(body, "EN")
        self.assertLessEqual(len(msg), WHATSAPP_MAX_BODY)
        self.assertTrue(meta.get("truncated") or meta.get("condensed"))


if __name__ == "__main__":
    unittest.main()
