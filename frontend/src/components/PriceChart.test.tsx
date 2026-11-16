import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PriceChart } from "./PriceChart";

describe("PriceChart empty engine response", () => {
  it("shows an unavailable state without rendering fabricated or invalid axes", () => {
    const { container } = render(<PriceChart
      symbol="NVDA"
      values={[]}
      referencePrice={142.68}
      interval="1M"
      style="Area"
      dataState="ready"
      useRawValues
      onStyleChange={vi.fn()}
      onExpand={vi.fn()}
      onRetry={vi.fn()}
    />);

    expect(screen.getByRole("status")).toHaveTextContent("No chart bars returned");
    expect(container.querySelector("svg[role='img']")).not.toBeInTheDocument();
    expect(container.textContent).not.toContain("NaN");
    expect(container.textContent).not.toContain("Infinity");
  });

  it("renders a single-bar interval without NaN SVG coordinates", () => {
    render(<PriceChart symbol="NVDA" values={[142.68]} referencePrice={142.68} interval="1D" style="Line" dataState="ready" onStyleChange={vi.fn()} onExpand={vi.fn()} onRetry={vi.fn()} useRawValues />);
    expect(screen.getByRole("img", { name: /NVDA 1D Python synthetic chart/ })).toBeInTheDocument();
    expect(document.querySelector("circle")?.getAttribute("cx")).not.toBe("NaN");
  });
});
