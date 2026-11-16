/** Explicit exchange-qualified symbols supported by the app's ticker picker. */
export const tradingViewSymbols: Record<string, string> = {
  NVDA: "NASDAQ:NVDA",
  AAPL: "NASDAQ:AAPL",
  MSFT: "NASDAQ:MSFT",
  AMZN: "NASDAQ:AMZN",
  GOOGL: "NASDAQ:GOOGL",
  JPM: "NYSE:JPM",
  LLY: "NYSE:LLY",
};

export const tradingViewTickerSymbols = Object.keys(tradingViewSymbols);
