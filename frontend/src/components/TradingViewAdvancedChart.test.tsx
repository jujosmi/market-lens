import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { TradingViewAdvancedChart } from "./TradingViewAdvancedChart";

afterEach(() => {
  for (const script of Array.from(document.head.querySelectorAll('script[data-tradingview-widget="true"]'))) script.dispatchEvent(new Event("error"));
  cleanup();
});

describe("TradingView advanced chart Web Component", () => {
  it("uses exchange-qualified symbols, the current official module, and an always-available provider link", () => {
    const { container } = render(<TradingViewAdvancedChart symbol="LLY" theme="light" />);
    const widget = container.querySelector("tv-advanced-chart");
    expect(widget).toHaveAttribute("symbol", "NYSE:LLY");
    expect(widget).toHaveAttribute("theme", "light");
    expect(widget).toHaveAttribute("interval", "1D");
    expect(document.head.querySelector('script[type="module"][src="https://widgets.tradingview-widget.com/w/en/tv-advanced-chart.js"]')).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open NYSE:LLY chart at TradingView" })).toHaveAttribute("href", "https://www.tradingview.com/symbols/NYSE-LLY/");
    expect(screen.getByText(/Jujosmi does not access or use widget data/)).toBeInTheDocument();
  });

  it("updates the official custom element when the selected ticker changes", () => {
    const { container, rerender } = render(<TradingViewAdvancedChart symbol="NVDA" />);
    expect(container.querySelector("tv-advanced-chart")).toHaveAttribute("symbol", "NASDAQ:NVDA");
    rerender(<TradingViewAdvancedChart symbol="AAPL" />);
    expect(container.querySelector("tv-advanced-chart")).toHaveAttribute("symbol", "NASDAQ:AAPL");
    expect(screen.getByRole("link", { name: "Open NASDAQ:AAPL chart at TradingView" })).toHaveAttribute("href", "https://www.tradingview.com/symbols/NASDAQ-AAPL/");
  });

  it("does not invent an exchange mapping for an unsupported ticker", () => {
    const { container } = render(<TradingViewAdvancedChart symbol="UNKNOWN" />);
    expect(container.querySelector("tv-advanced-chart")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("No exchange-qualified TradingView symbol is configured for UNKNOWN");
  });
});
