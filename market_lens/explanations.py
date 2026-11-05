"""Plain-language explanations for the dashboard's calculated readings."""

from __future__ import annotations

import numpy as np


def rating_explanation(stats: dict) -> str:
    """Explain the rating while tolerating older cached calculation results."""
    checks = stats.get("rating_check_details")
    if not checks:
        net = stats.get("constructive_checks", 0) - stats.get("caution_checks", 0)
        checks_complete = stats.get("rating_checks_complete", stats.get("rating") != "Unavailable")
        if not checks_complete:
            return ("No rating is shown because one or more required indicators are unavailable. "
                    "The screen needs full trend, momentum, relative-return and drawdown inputs.")
        return (f"{stats.get('rating', 'Unavailable')} uses five equally weighted constructive and five caution checks. "
                f"Current counts are {stats.get('constructive_checks', 0)} constructive and "
                f"{stats.get('caution_checks', 0)} caution (net {net:+d}); a difference of +2 gives Buy, "
                "−2 gives Sell, otherwise Hold. This is a technical screen, not a forecast.")
    missing = [check["label"] for check in checks if check["passed"] is None]
    if not stats.get("rating_checks_complete", False):
        sample = "; ".join(missing[:3])
        more = "…" if len(missing) > 3 else ""
        return (f"No rating is shown because {len(missing)} of the 10 checks are unavailable: "
                f"{sample}{more}. A check needs its full history window.")
    passed = [check["label"] for check in checks if check["passed"] is True]
    net = stats["constructive_checks"] - stats["caution_checks"]
    threshold = "Buy" if net >= 2 else "Sell" if net <= -2 else "Hold"
    supporting = "; ".join(passed[:3]) if passed else "no directional checks passed"
    return (f"{stats['rating']} because {stats['constructive_checks']} constructive checks minus "
            f"{stats['caution_checks']} caution checks gives {net:+d} (rule result: {threshold}). "
            f"Signals: {supporting}. Checks are equally weighted and are not a forecast.")


def trend_explanation(stats: dict) -> str:
    """Explain the moving-average alignment and any history requirement."""
    if not np.isfinite(stats["sma200"]):
        observations = stats.get("observations", "an unavailable number of")
        return (f"{stats['state']}. The trend label compares the latest close with full 50-session and "
                f"200-session averages; this ticker has {observations} closes and needs 200 for the long-term comparison.")
    return (f"{stats['state']}. Latest close ${stats['last']:,.2f}; 50-session average "
            f"${stats['sma50']:,.2f}; 200-session average ${stats['sma200']:,.2f}. "
            "Both averages use complete windows.")
