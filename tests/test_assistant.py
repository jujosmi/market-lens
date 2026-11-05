import io
import json
import unittest
from unittest.mock import patch

from market_lens.assistant import ask_ai, explain_from_glossary


class AssistantTests(unittest.TestCase):
    def test_offline_glossary_explains_a_known_term(self):
        response = explain_from_glossary("Can you explain RSI simply?")
        self.assertIn("Relative Strength Index", response)
        self.assertIn("guarantees a reversal", response)

    def test_no_key_uses_glossary_without_network(self):
        with patch("market_lens.assistant.urlopen") as urlopen:
            response = ask_ai([{"role":"user", "content":"What is beta?"}], api_key="")
        self.assertIn("Beta estimates", response)
        urlopen.assert_not_called()

    def test_ai_call_keeps_key_in_server_request_and_parses_response(self):
        answer = {"output":[{"type":"message", "content":[{"type":"output_text", "text":"Beta compares returns."}]}]}
        fake_response = io.BytesIO(json.dumps(answer).encode("utf-8"))
        with patch("market_lens.assistant.urlopen", return_value=fake_response) as urlopen:
            response = ask_ai([{"role":"user", "content":"What is beta?"}], api_key="secret-test-key")
        self.assertEqual(response, "Beta compares returns.")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-test-key")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertFalse(payload["store"])
        self.assertEqual(payload["input"][0]["content"], "What is beta?")


if __name__ == "__main__":
    unittest.main()
