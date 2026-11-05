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
