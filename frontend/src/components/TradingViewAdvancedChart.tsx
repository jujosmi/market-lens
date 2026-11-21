import { tradingViewSymbols } from "../data/tradingViewSymbols";
import { TradingViewWidget } from "./TradingViewWidget";

type Props = { symbol: string; theme?: "dark" | "light" };
const ADVANCED_CHART_MODULE = "https://widgets.tradingview-widget.com/w/en/tv-advanced-chart.js";

/** Official TradingView embed. The app never reads widget content or market data. */
export function TradingViewAdvancedChart({ symbol, theme = "dark" }: Props) {
  const qualifiedSymbol = tradingViewSymbols[symbol];
  if (!qualifiedSymbol) return <div className="workspace-state" role="status">No exchange-qualified TradingView symbol is configured for {symbol}.</div>;
  const providerUrl = `https://www.tradingview.com/symbols/${qualifiedSymbol.replace(":", "-")}/`;
  return <div className="tradingview-chart-frame" aria-label={`${qualifiedSymbol} TradingView advanced chart`}>
    <TradingViewWidget
      scriptUrl={ADVANCED_CHART_MODULE}
      tagName="tv-advanced-chart"
      attributes={{ symbol: qualifiedSymbol, interval: "1D", theme, timezone: "Etc/UTC" }}
      providerUrl={providerUrl}
      providerLinkLabel={`Open ${qualifiedSymbol} chart at TradingView`}
      height={550}
      label={`${qualifiedSymbol} TradingView advanced chart`}
      className="tradingview-advanced-chart"
    />
    <p className="chart-data-notice">Chart is provided directly by TradingView. Jujosmi does not access or use widget data in its calculations. Use the ticker selector above to keep the app’s selected symbol in sync.</p>
  </div>;
}
