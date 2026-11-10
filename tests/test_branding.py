from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import app


ROOT = Path(__file__).resolve().parents[1]


class PublicBrandingTests(unittest.TestCase):
    def test_streamlit_browser_title_uses_approved_public_name(self):
        with (
            patch.dict(os.environ, {"MARKET_LENS_PUBLIC": "", "MARKET_LENS_HOSTED": ""}),
            patch.object(app.st, "set_page_config") as set_page_config,
            patch.object(app.st, "markdown"),
        ):
            app.configure_app()

        self.assertEqual(set_page_config.call_args.kwargs["page_title"], "Jujosmi Trade")

    def test_streamlit_visible_brand_uses_existing_jujosmi_logo(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        logo = ROOT / "static" / "jujosmi-logo-simple-shadow.png"

        self.assertTrue(logo.is_file())
        self.assertIn("jujosmi-logo-simple-shadow.png", source)
        self.assertIn("JUJOSMI TRADE", source)
        self.assertIn("<h1>Jujosmi Trade</h1>", source)

    def test_embed_branding_keeps_existing_origin_and_ready_message(self):
        app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        shell = (ROOT / "website_embed" / "index.html").read_text(encoding="utf-8")
        snippet = (ROOT / "website_embed" / "market-lens-iframe.html").read_text(encoding="utf-8")

        self.assertIn("<title>Jujosmi Trade | Jujosmi Labs</title>", shell)
        self.assertIn('property="og:title" content="Jujosmi Trade | Jujosmi Labs"', shell)
        self.assertIn('title="Jujosmi Trade stock research dashboard"', shell)
        self.assertIn('src="https://jjs-marketlens.streamlit.app/"', shell)
        self.assertIn('title="Jujosmi Trade stock research dashboard"', snippet)
        self.assertIn('src="https://YOUR-MARKET-LENS-APP.streamlit.app/?embed=true"', snippet)

        producer = re.search(
            r'type:"([^"]+)",token:"([^"]+)"', app_source
        )
        consumer_type = re.search(r'event\.data\?\.type === "([^"]+)"', snippet)
        consumer_token = re.search(r'event\.data\?\.token === "([^"]+)"', snippet)
        self.assertIsNotNone(producer)
        self.assertIsNotNone(consumer_type)
        self.assertIsNotNone(consumer_token)
        self.assertEqual(producer.group(1), consumer_type.group(1))
        self.assertEqual(producer.group(2), consumer_token.group(1))


if __name__ == "__main__":
    unittest.main()
