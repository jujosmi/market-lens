import { useEffect, useRef } from "react";
import { tradingViewSymbols } from "../data/tradingViewSymbols";

type Props = { symbol: string; theme?: "dark" | "light" };

/** Official TradingView embed. The app never reads the widget iframe or its market data. */
export function TradingViewAdvancedChart({ symbol, theme = "dark" }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const qualifiedSymbol = tradingViewSymbols[symbol];

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !qualifiedSymbol) return;
    let active = true;
    for (const child of Array.from(host.children)) {
      if ((child as HTMLElement).dataset.tvSettled === "true") child.remove();
    }

    const generation = document.createElement("div");
    generation.className = "tradingview-widget-generation";
    generation.dataset.tvSettled = "false";
    const widget = document.createElement("div");
    widget.className = "tradingview-widget-container__widget";
    const attribution = document.createElement("div");
    attribution.className = "tradingview-widget-copyright";
    const link = document.createElement("a");
    link.href = `https://www.tradingview.com/symbols/${qualifiedSymbol.replace(":", "-")}/`;
    link.target = "_blank";
    link.rel = "noopener nofollow";
    link.textContent = `${qualifiedSymbol} chart`;
    const brand = document.createElement("span");
    brand.textContent = " by TradingView";
    attribution.append(link, brand);
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.async = true;
    script.textContent = JSON.stringify({
      autosize: true,
      symbol: qualifiedSymbol,
      interval: "D",
      timezone: "Etc/UTC",
      theme,
      style: "1",
      locale: "en",
      allow_symbol_change: true,
      calendar: false,
      support_host: "https://www.tradingview.com",
    });
    generation.append(widget, attribution, script);
    host.append(generation);

    const handleLoad = () => {
      generation.dataset.tvSettled = "true";
      if (!active) {
        generation.remove();
        return;
      }
      for (const child of Array.from(host.children)) {
        if (child !== generation && (child as HTMLElement).dataset.tvSettled === "true") child.remove();
      }
    };
    const handleError = () => generation.remove();
    script.addEventListener("load", handleLoad);
    script.addEventListener("error", handleError, { once: true });

    return () => {
      active = false;
      script.removeEventListener("error", handleError);
      // Keep a pending script attached to its container until it settles. The embed reads
      // currentScript.parentNode during initialization; detaching it early caused a
      // third-party querySelector error when a symbol changed or the component unmounted.
      if (generation.dataset.tvSettled === "true") generation.remove();
    };
  }, [qualifiedSymbol, theme]);

  if (!qualifiedSymbol) return <div className="workspace-state" role="status">No exchange-qualified TradingView symbol is configured for {symbol}.</div>;
  return <div className="tradingview-chart-frame" aria-label={`${qualifiedSymbol} TradingView advanced chart`}>
    <div ref={hostRef} className="tradingview-widget-container" />
    <p className="chart-data-notice">Chart is provided directly by TradingView. Jujosmi does not access or use widget data in its calculations. A symbol chosen inside the embedded chart does not change Jujosmi’s selected ticker; use the selector above to keep the app in sync.</p>
  </div>;
}
