from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from market_lens.ui.components import (
    render_company_header, render_financial_table, render_headline_card,
    render_metric_card, render_section_heading, render_workspace_heading,
)


class DashboardComponentTests(unittest.TestCase):
    def test_company_header_presents_identity_price_and_freshness_safely(self):
        with patch("market_lens.ui.components.st.markdown") as markdown:
            render_company_header(
                name="Example <Co>", symbol="EXM", exchange="Nasdaq",
                sector="Technology", industry="Software", price="$123.45",
                daily_change="+1.25% today", change_positive=True,
                source="Yahoo Finance", retrieved="2026-11-08 10:00 ET",
                interval="1 day", status="recent", latest_bar="2026-11-07",
                quote_delay="unknown",
            )
        rendered = markdown.call_args.args[0]
        self.assertIn("Example &lt;Co&gt;", rendered)
        self.assertIn("Nasdaq", rendered)
        self.assertIn("Technology", rendered)
        self.assertIn("$123.45", rendered)
        self.assertIn("+1.25% today", rendered)
        self.assertIn("Yahoo Finance", rendered)
        self.assertIn("recent", rendered)
        self.assertIn('class="company-change positive"', rendered)

    def test_metric_card_exposes_explanation_and_escapes_provider_text(self):
        with patch("market_lens.ui.components.st.markdown") as markdown:
            render_metric_card("Expected move", "+/-5.0%", "Non-directional range", "A <risk> range.")
        rendered = markdown.call_args.args[0]
        self.assertIn("Expected move", rendered)
        self.assertIn("Non-directional range", rendered)
        self.assertIn("A &lt;risk&gt; range.", rendered)
        self.assertIn('<details class="help-icon">', rendered)
        self.assertIn('<summary aria-label="Why Expected move?">', rendered)


    def test_metric_explanation_uses_native_keyboard_and_touch_disclosure(self):
        with patch("market_lens.ui.components.st.markdown") as markdown:
            render_metric_card("Signal rating", "Hold", "Technical screen", "Trend and momentum remain mixed.")
        rendered = markdown.call_args.args[0]
        self.assertIn('<details class="help-icon">', rendered)
        self.assertIn('<summary aria-label="Why Signal rating?">', rendered)
        self.assertIn('aria-hidden="true">i</span>', rendered)
        self.assertIn("Trend and momentum remain mixed.", rendered)
        self.assertNotIn('role="button"', rendered)
        self.assertNotIn('tabindex=', rendered)
        app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8-sig")
        self.assertIn(".help-icon > summary:focus-visible", app_source)
        self.assertIn(".help-icon[open] .metric-tooltip", app_source)
        self.assertIn("width:min(280px,calc(100vw - 40px))", app_source)


    def test_headline_card_keeps_sentiment_publisher_date_and_source_link_visible(self):
        with patch("market_lens.ui.components.st.markdown") as markdown:
            render_headline_card(
                title="Company <update>", sentiment="Neutral", confidence="Medium",
                topic="Earnings", publisher="Publisher One", published_at="Nov 8, 10:00 AM",
                reason="No company-specific direction.", source_url="https://example.com/story",
            )
        rendered = markdown.call_args.args[0]
        for expected in ("Company &lt;update&gt;", "NEUTRAL", "Publisher One", "Nov 8, 10:00 AM", "Open original source", "https://example.com/story"):
            self.assertIn(expected, rendered)

    def test_headline_without_safe_source_does_not_render_placeholder_link(self):
        with patch("market_lens.ui.components.st.markdown") as markdown:
            render_headline_card(
                title="Headline", sentiment="Neutral", confidence="Low", topic="General",
                publisher="Publisher", published_at="Recent", reason="Weak signal", source_url="javascript:alert(1)",
            )
        rendered = markdown.call_args.args[0]
        self.assertNotIn('href="#"', rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn("Source link unavailable", rendered)

    def test_dashboard_css_defines_compact_and_mobile_layout_rules(self):
        app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 900px)", app_source)
        self.assertIn("@media (max-width: 640px)", app_source)
        self.assertIn("@media (max-width: 430px)", app_source)
        self.assertIn(".st-key-market_chart_controls", app_source)
        self.assertIn(".company-header", app_source)

    def test_mobile_css_reduces_crowding_without_hiding_financial_panels(self):
        app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        mobile_rules = app_source.split("@media (max-width: 640px)", 1)[1].split("@media (max-width: 430px)", 1)[0]
        self.assertIn('[data-testid="stMainBlockContainer"] { padding:12px 12px 48px; }', mobile_rules)
        self.assertIn('st-key-market_chart_shell [data-testid="stVerticalBlockBorderWrapper"] { padding:12px 10px; }', mobile_rules)
        self.assertIn("grid-template-columns:minmax(0,1fr); gap:8px;", mobile_rules)
        self.assertIn('div[data-testid="stDataFrame"] { max-width:100%; min-width:0; overflow-x:auto; }', mobile_rules)
        self.assertIn('[data-testid="stButton"] button { min-height:42px; }', mobile_rules)
        self.assertIn('[data-testid="stExpander"] summary { min-height:44px; }', mobile_rules)
        self.assertNotIn("display:none", mobile_rules)
        self.assertNotIn("visibility:hidden", mobile_rules)

    def test_workspace_heading_is_contextual_and_escapes_content(self):
        with patch("market_lens.ui.components.st.markdown") as markdown:
            render_workspace_heading("Company <Research>", "Review facts & estimates.")
        rendered = markdown.call_args.args[0]
        self.assertIn('class="workspace-heading"', rendered)
        self.assertIn("Jujosmi Trade · Research workspace", rendered)
        self.assertIn("Company &lt;Research&gt;", rendered)
        self.assertIn("Review facts &amp; estimates.", rendered)

    def test_market_overview_places_full_width_chart_before_snapshot(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8-sig")
        overview = source.split('    if workspace == "Market Overview":', 1)[1].split('    if workspace == "Discovery":', 1)[0]
        self.assertIn('key="market_chart_shell"', overview)
        self.assertIn('key="market_chart_main"', overview)
        self.assertLess(overview.index('render_section_heading("Price chart"'), overview.index('render_section_heading("Selected ticker snapshot"'))
        for key in ("market_chart_interval", "market_chart_style", "market_chart_averages", "market_chart_range", "market_chart_open_fullscreen"):
            self.assertIn(key, overview)
        self.assertIn('with st.expander("Market read · trend, momentum, and volatility context"', overview)

    def test_section_heading_and_financial_table_use_shared_rendering_contract(self):
        with patch("market_lens.ui.components.st.markdown") as markdown:
            render_section_heading("Valuation", "Reported profile data", "Business & valuation")
        self.assertIn("Valuation", markdown.call_args.args[0])
        with patch("market_lens.ui.components.st.dataframe") as dataframe:
            render_financial_table([{"Revenue": 1.0}], column_config={"Revenue":"fixture"}, key="revenue")
        self.assertEqual(dataframe.call_args.kwargs["width"], "stretch")
        self.assertEqual(dataframe.call_args.kwargs["column_config"], {"Revenue":"fixture"})
        self.assertEqual(dataframe.call_args.kwargs["key"], "revenue")


if __name__ == "__main__":
    unittest.main()


