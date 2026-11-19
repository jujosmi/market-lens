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
    const staleScript = container.querySelector("script");
    const staleGeneration = staleScript?.parentElement;
    rerender(<TradingViewAdvancedChart symbol="AAPL" />);
    await waitFor(() => {
      const scripts = Array.from(container.querySelectorAll("script"));
      expect(scripts.some((script) => JSON.parse(script.textContent ?? "{}").symbol === "NASDAQ:AAPL")).toBe(true);
    });
    expect(staleScript?.parentElement).toBe(staleGeneration);
    staleScript?.dispatchEvent(new Event("load"));
    await waitFor(() => expect(staleGeneration?.parentElement).toBeNull());
    expect(Array.from(container.querySelectorAll("script")).some((script) => JSON.parse(script.textContent ?? "{}").symbol === "NASDAQ:AAPL")).toBe(true);
  });

  it("keeps an initializing embed attached until its script settles after unmount", () => {
    const { container, unmount } = render(<TradingViewAdvancedChart symbol="NVDA" />);
    const script = container.querySelector("script");
    const generation = script?.parentElement;
    unmount();
    expect(script?.parentElement).toBe(generation);
    expect(script?.isConnected).toBe(false);
    script?.dispatchEvent(new Event("load"));
    expect(generation?.parentElement).toBeNull();
  });
});
