"""Plain-language explanations for the dashboard's calculated readings."""

from __future__ import annotations

import numpy as np


def rating_explanation(stats: dict) -> str:
    """Explain the technical rating, its threshold, and its difference from consensus."""
    checks = stats.get("rating_check_details")
    constructive = int(stats.get("constructive_checks", 0))
    caution = int(stats.get("caution_checks", 0))
    net = constructive - caution
    checks_complete = stats.get("rating_checks_complete", stats.get("rating") != "Unavailable")
    if checks and not checks_complete:
        missing = [check["label"] for check in checks if check["passed"] is None]
        sample = "; ".join(missing[:2])
        more = "…" if len(missing) > 2 else ""
        return (f"No Market Lens signal is shown because {len(missing)} of 10 technical checks are unavailable: "
                f"{sample}{more}. The screen requires complete 50/200-day trend, MACD, 3-month relative-return, "
                "RSI, and 52-week drawdown inputs. Analyst consensus is a separate measure.")
    if not checks_complete:
        return ("No Market Lens signal is shown because one or more full technical-history inputs are unavailable. "
                "The analyst consensus rating, if shown elsewhere, is a separate measure.")

    positives = [check["label"] for check in checks or []
                 if check.get("side") == "Constructive" and check.get("passed") is True]
    cautions = [check["label"] for check in checks or []
                if check.get("side") == "Caution" and check.get("passed") is True]
    threshold = "Buy" if net >= 2 else "Sell" if net <= -2 else "Hold"
    details = []
    if positives:
        details.append("constructive: " + "; ".join(positives[:2]) + ("; …" if len(positives) > 2 else ""))
    if cautions:
        details.append("caution: " + "; ".join(cautions[:2]) + ("; …" if len(cautions) > 2 else ""))
    signals = " Passed checks: " + " | ".join(details) + "." if details else " No directional checks passed."
    rating = stats.get("rating", threshold)
    return (f"{rating} is Market Lens's technical screen: {constructive}/5 constructive minus {caution}/5 caution "
            f"checks = {net:+d}. Buy requires +2 or more; Sell requires −2 or less; Hold is −1 to +1. "
            f"All 10 checks must be available. Analyst consensus may differ.{signals} This is a screening label, not a trade recommendation.")


def trend_explanation(stats: dict) -> str:
    """Explain the moving-average alignment and any history requirement."""
    if not np.isfinite(stats["sma200"]):
        observations = stats.get("observations", "an unavailable number of")
        return (f"{stats['state']}. The trend label compares the latest close with full 50-session and "
                f"200-session averages; this ticker has {observations} closes and needs 200 for the long-term comparison.")
    return (f"{stats['state']}. Latest close ${stats['last']:,.2f}; 50-session average "
            f"${stats['sma50']:,.2f}; 200-session average ${stats['sma200']:,.2f}. "
            "Both averages use complete windows.")
