"""Small, stable application configuration."""

SECTORS = {
    "Technology":"XLK", "Financials":"XLF", "Health care":"XLV", "Consumer discretionary":"XLY",
    "Communication services":"XLC", "Industrials":"XLI", "Consumer staples":"XLP",
    "Energy":"XLE", "Utilities":"XLU", "Materials":"XLB", "Real estate":"XLRE",
}

SECTOR_KEYS = [
    "technology", "communication-services", "consumer-cyclical", "consumer-defensive",
    "energy", "financial-services", "healthcare", "industrials", "basic-materials",
    "real-estate", "utilities",
]

DEFAULT_WATCHLIST = ["NVDA", "AAPL", "TSLA"]
MAX_WATCHLIST_SIZE = 8
DATA_PROVIDER_NAME = "Yahoo Finance via yfinance"


def setting_enabled(value: object) -> bool:
    """Interpret a deployment boolean without treating arbitrary text as true."""
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def hosted_watchlist_mode(environment_value: object = "", secret_value: object = "") -> bool:
    """Return whether hosted visitors use session-isolated watchlists."""
    return setting_enabled(environment_value) or setting_enabled(secret_value)


def public_watchlist_guard(public_environment_value: object = "", public_secret_value: object = "",
                           hosted_environment_value: object = "", hosted_secret_value: object = "") -> str | None:
    """Fail closed when a deployment declares itself public but is not isolated."""
    is_public = setting_enabled(public_environment_value) or setting_enabled(public_secret_value)
    is_hosted = hosted_watchlist_mode(hosted_environment_value, hosted_secret_value)
    if is_public and not is_hosted:
        return ("Public deployment requires MARKET_LENS_HOSTED=true. "
                "Set MARKET_LENS_HOSTED=true to keep watchlists session-isolated.")
    return None
