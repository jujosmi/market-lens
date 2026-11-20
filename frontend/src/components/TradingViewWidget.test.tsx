import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { TradingViewWidget } from "./TradingViewWidget";

afterEach(() => {
  for (const script of Array.from(document.head.querySelectorAll('script[data-tradingview-widget="true"]'))) script.dispatchEvent(new Event("error"));
  cleanup();
});

describe("TradingView Web Component loader", () => {
  it("shows a clear provider fallback after a script load failure", async () => {
    render(<TradingViewWidget scriptUrl="https://widgets.example.test/news.js" tagName="tv-news-failure-case" attributes={{ symbol: "NASDAQ:AAPL" }} providerUrl="https://www.tradingview.com/symbols/NASDAQ-AAPL/news/" providerLinkLabel="Open provider news" height={400} label="AAPL provider news" />);
    expect(document.querySelector("tv-news-failure-case")).toHaveAttribute("symbol", "NASDAQ:AAPL");
    const script = document.head.querySelector('script[src="https://widgets.example.test/news.js"]');
    expect(script).toBeInTheDocument();
    act(() => script?.dispatchEvent(new Event("error")));
    expect(await screen.findByRole("alert")).toHaveTextContent("widget script could not be loaded");
    expect(screen.getByRole("link", { name: "Open provider news" })).toHaveAttribute("href", "https://www.tradingview.com/symbols/NASDAQ-AAPL/news/");
    expect(screen.getByRole("button", { name: "Retry widget" })).toBeInTheDocument();
  });

  it("reports module registration while preserving an always-visible provider link", async () => {
    render(<TradingViewWidget scriptUrl="https://widgets.example.test/ta.js" tagName="tv-test-analysis-widget" attributes={{ symbol: "NASDAQ:MSFT", theme: "dark" }} providerUrl="https://www.tradingview.com/symbols/NASDAQ-MSFT/technicals/" providerLinkLabel="Open provider technicals" height={400} label="MSFT provider technicals" />);
    const script = document.head.querySelector('script[src="https://widgets.example.test/ta.js"]');
    expect(script).toBeInTheDocument();
    act(() => {
      customElements.define("tv-test-analysis-widget", class extends HTMLElement {});
      script?.dispatchEvent(new Event("load"));
    });
    expect(await screen.findByRole("status")).toHaveTextContent("widget module loaded");
    expect(screen.getByRole("link", { name: "Open provider technicals" })).toHaveAttribute("href", "https://www.tradingview.com/symbols/NASDAQ-MSFT/technicals/");
  });
});
