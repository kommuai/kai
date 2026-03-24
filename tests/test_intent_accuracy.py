import unittest

from support_runtime.router import IntentRouter


class IntentAccuracyTests(unittest.TestCase):
    def test_keyword_routing_accuracy_50_plus(self):
        router = IntentRouter()
        router.load()
        samples = [
            ("can i install now", "known_faq_intent"),
            ("installation appointment", "known_faq_intent"),
            ("where is your office", "known_faq_intent"),
            ("what is pricing", "known_faq_intent"),
            ("rto details", "known_faq_intent"),
            ("how long install", "known_faq_intent"),
            ("refund policy", "unsafe_human_escalation"),
            ("i want human agent", "unsafe_human_escalation"),
            ("cancel order now", "unsafe_human_escalation"),
            ("order status please", "account_order_status_intent"),
            ("tracking shipment", "account_order_status_intent"),
            ("payment status", "account_order_status_intent"),
            ("is myvi supported", "vehicle_support_check_intent"),
            ("is this car supported", "vehicle_support_check_intent"),
            ("can bus support", "vehicle_support_check_intent"),
            ("does it have lka", "vehicle_support_check_intent"),
            ("flexray vehicle", "vehicle_support_check_intent"),
            ("ABC12345", "warranty_lookup_intent"),
            ("check warranty de6538b603303777", "warranty_lookup_intent"),
            ("waranti dongle", "warranty_lookup_intent"),
            ("KA2 error 1003", "troubleshooting_intent"),
            ("device issue not working", "troubleshooting_intent"),
            ("diagnostic issue", "troubleshooting_intent"),
            ("ka1 overheating", "troubleshooting_intent"),
            ("gps issue", "troubleshooting_intent"),
            ("ka2 reboot loop", "troubleshooting_intent"),
            ("device cannot turn on", "troubleshooting_intent"),
            ("software reset procedure", "known_faq_intent"),
            ("batch status eta", "known_faq_intent"),
            ("what is kommuassist", "known_faq_intent"),
            ("difference ka1 ka2", "known_faq_intent"),
            ("max speed", "known_faq_intent"),
            ("shipping schedule", "known_faq_intent"),
            ("sim usage", "known_faq_intent"),
            ("can use hotspot", "known_faq_intent"),
            ("legality malaysia", "known_faq_intent"),
            ("test drive available", "known_faq_intent"),
            ("transfer device", "known_faq_intent"),
            ("borrow my car for support", "vehicle_support_check_intent"),
            ("unsupported car", "vehicle_support_check_intent"),
            ("warranty period", "known_faq_intent"),
            ("how to reset", "known_faq_intent"),
            ("delivery batch tracking", "known_faq_intent"),
            ("office location", "known_faq_intent"),
            ("book installation", "known_faq_intent"),
            ("monthly payment plan", "known_faq_intent"),
            ("is bmw flexray", "vehicle_support_check_intent"),
            ("need live agent now", "unsafe_human_escalation"),
            ("help angry complaint", "unsafe_human_escalation"),
            ("where my order", "account_order_status_intent"),
            ("track my shipment now", "account_order_status_intent"),
            ("paid already payment status", "account_order_status_intent"),
        ]
        correct = 0
        for text, expected in samples:
            route, _conf, _intent = router.route(text)
            if route == expected:
                correct += 1
        self.assertGreaterEqual(len(samples), 50)
        self.assertGreaterEqual(correct / len(samples), 0.75)


if __name__ == "__main__":
    unittest.main()

