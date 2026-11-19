import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { KestrelResearchPreview } from "./KestrelResearchPreview";

const makePayload = (scenario: "complete" | "missing_intraday_segment" = "complete") => {
  const gap = scenario === "missing_intraday_segment";
  return {
    preview_contract_id: "JUJOSMI_TRADE_KESTREL_LOCAL_PREVIEW_V1", status: "accepted", source_mode: "synthetic_offline_only",
    freshness: "stale", stale: true, current_market_data: false, age_hours: 12000, retrieved_at_utc: "2026-11-18T12:00:00Z",
    bundle: { record: {
      bridge_contract_id: "KESTREL_TRADE_RESEARCH_BRIDGE_V1", schema_version: 1, record_type: "descriptive_research",
      producer_id: "KESTREL_M9_13_OPERATIONAL_SPY_RESEARCH", source_mode: "synthetic_offline_only", scenario_id: scenario,
      instrument: { instrument_id: "JLC:US_ETF:SPY", symbol: "SPY" },
      observation_timing: { observation_timestamp_utc: "2025-06-02T16:30:00Z", availability_timestamp_utc: "2025-06-02T16:30:00Z", served_at_utc: "2025-06-02T16:30:00Z" },
      research_status: { outcome: "partial", completeness_status: "partial", classification_type: "descriptive_technical_state", classification: gap ? "daily_only" : "directionally_aligned" },
      m913_quality_notes: gap ? ["missing_intraday_bars:1"] : [],
      source_provenance: { daily: { source_provider: "synthetic_provider_shape_v1" }, intraday: { source_provider: "synthetic_provider_shape_v1" } },
      research_response: { contract_id: "KESTREL_RESEARCH_API_V1", schema_version: 1, outcome: "partial", request: { as_of_utc: "2025-06-02T16:30:00Z" }, data_use: { public_display_authorized: false },
        research_record: { completeness_status: "partial", unified_descriptive_classification: gap ? "daily_only" : "directionally_aligned", classification_type: "descriptive_technical_state",
          daily_context: { trend_classification: "bullish", momentum_classification: "positive", volatility_classification: "low", volume_confirmation: "unavailable" },
          intraday_context: { trend_1m: gap ? "unavailable" : "bullish", trend_5m: gap ? "unavailable" : "bullish", price_vs_vwap: gap ? "unavailable" : "above_vwap", data_quality_status: gap ? "partial" : "valid" },
          data_quality_flags: gap ? ["intraday_context_incomplete_or_unavailable"] : [], abstention_reasons: ["sample_abstention"],
          research_use_restrictions: ["synthetic_fixture_only"] } }
    }, manifest: { schema_version: 1, m95_schema_sha256: "4d7b99d4e0e7e601b3729bee5da51e5da8d2c0f29a9f454c356b51639a48d32e",
      m97_schema_sha256: "33ad7e58151dde43470ff7b272820dd8c9b4b75d554911e250abcb4c9f54c11f", record_sha256: "a".repeat(64), manifest_sha256: "b".repeat(64) } }
  };
};

afterEach(() => vi.unstubAllGlobals());

describe("Kestrel local research preview", () => {
  it("renders descriptive research with the historical synthetic warning", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(makePayload()), { status: 200 })));
    render(<KestrelResearchPreview />);
    expect(await screen.findByRole("heading", { name: "Kestrel Research — Development Preview" })).toBeInTheDocument();
    expect(await screen.findByText("directionally aligned")).toBeInTheDocument();
    expect(screen.getByText(/Not current market data/)).toBeInTheDocument();
    expect(screen.getByText(/historical and stale/)).toBeInTheDocument();
  });

  it("preserves unavailable intraday values for the missing segment case", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(makePayload("missing_intraday_segment")), { status: 200 })));
    render(<KestrelResearchPreview />);
    await waitFor(() => expect(screen.getAllByText("unavailable").length).toBeGreaterThanOrEqual(3));
    expect(screen.getByText("daily only")).toBeInTheDocument();
  });

  it("handles an unavailable route without exposing a path and retries the fixed endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Research preview is unavailable." }), { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<KestrelResearchPreview />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("preview is unavailable");
    expect(alert.textContent).not.toMatch(/[A-Z]:\\/);
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(String(fetchMock.mock.calls[0][0])).toContain("/dev/kestrel/research");
  });
});