import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TradingViewAdvancedChart } from "./TradingViewAdvancedChart";

describe("TradingView advanced chart embed", () => {
  it("uses exchange-qualified configuration, native controls, and TradingView attribution", async () => {
    const { container } = render(<TradingViewAdvancedChart symbol="LLY" theme="light" />);
    await waitFor(() => expect(container.querySelector("script[src*='embed-widget-advanced-chart.js']")).toBeInTheDocument());
    const config = JSON.parse(container.querySelector("script")?.textContent ?? "{}");
    expect(config).toMatchObject({ symbol: "NYSE:LLY", theme: "light", allow_symbol_change: true, autosize: true });
    expect(container.querySelector(".tradingview-widget-copyright")).toHaveTextContent("by TradingView");
  });

  it("remounts configuration when a selected ticker changes without accessing iframe content", async () => {
    const { container, rerender } = render(<TradingViewAdvancedChart symbol="NVDA" />);
    rerender(<TradingViewAdvancedChart symbol="AAPL" />);
    await waitFor(() => {
      const script = container.querySelector("script");
      expect(JSON.parse(script?.textContent ?? "{}").symbol).toBe("NASDAQ:AAPL");
    });
    expect(container.querySelectorAll("script")).toHaveLength(1);
  });
});
