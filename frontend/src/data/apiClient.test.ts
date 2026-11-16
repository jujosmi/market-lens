import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, fetchChart, fetchDiscovery, fetchDiscoveryCalendar, fetchOverview, fetchWatchlistSummaries } from "./apiClient";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe("typed local API client", () => {
  it("validates overview response shapes before returning data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      data: { markets: [{ name: "Sample", symbol: "SMP", value: "10.00", change: "+1%", tone: "up", series: [1, 2, 3] }], sector_activity: [], disclosure: "Synthetic only." },
      status: "ok", source: "synthetic-fixtures", freshness: "simulated", warnings: [],
    }), { status: 200, headers: { "Content-Type": "application/json" } })));
    const response = await fetchOverview();
    expect(response.data?.markets[0]?.symbol).toBe("SMP");
  });

  it("preserves provider rate-limit and stale-data metadata", async () => {
    const payload = { data: { markets: [], sector_activity: [], disclosure: "Synthetic only." }, status: "partial", source: "synthetic-fixtures", freshness: "simulated", warnings: ["Showing stale data."], missing_fields: [], stale: true };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } })));
    const result = await fetchOverview();
    expect(result.status).toBe("partial");
    expect(result.stale).toBe(true);
    expect(result.warnings[0]).toBe("Showing stale data.");
  });

  it("classifies an API rate limit without converting it to a generic failure", async () => {
    const payload = { data: null, status: "rate_limited", source: "synthetic-fixtures", freshness: "simulated", warnings: ["Provider request limit reached."] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 429 })));
    await expect(fetchOverview()).rejects.toMatchObject({ status: "rate_limited", httpStatus: 429 });
  });

  it("rejects malformed provider-shaped payloads without exposing their body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ token: "secret", data: {}, status: "ok", source: "other", freshness: "now", warnings: [] }), { status: 200 })));
    await expect(fetchOverview()).rejects.toMatchObject({ message: "The local API response did not match the expected contract.", status: "failed" });
  });

  it("preserves bounded Discovery filters in the request URL", async () => {
    const payload = { data: { sectors: [], industries: [], companies: [], selected_sector: "Technology", selected_industry: "Semiconductors", query: "NV", disclosure: "Synthetic only." }, status: "ok", source: "synthetic-fixtures", freshness: "simulated", warnings: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchDiscovery({ sector: "Technology", industry: "Semiconductors", query: "NV" });
    const requested = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(requested.searchParams.get("sector")).toBe("Technology");
    expect(requested.searchParams.get("industry")).toBe("Semiconductors");
    expect(requested.searchParams.get("q")).toBe("NV");
  });

  it("reports API unavailable separately from malformed input and failed requests", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ data: null, status: "unavailable", source: "synthetic-fixtures", freshness: "simulated", warnings: ["No matching fixture."] }), { status: 404 }))));
    let caught: unknown;
    try { await fetchOverview(); } catch (error) { caught = error; }
    expect(caught).toBeInstanceOf(ApiRequestError);
    expect(caught).toMatchObject({ status: "unavailable", httpStatus: 404 });
  });

  it("requests an explicit synthetic chart interval", async () => {
    const payload = { data: { symbol: "NVDA", range: "1D", interval: "30m", bars: [{ time: "SAMPLE+001", open: 1, high: 2, low: 0.5, close: 1.5, volume: 100 }], label: "Synthetic interpolation, not historical market data" }, status: "ok", source: "python-engine-snapshot", freshness: "simulated", missing_fields: [], warnings: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await fetchChart("NVDA", "1D", "30m");
    expect(result.data?.interval).toBe("30m");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("interval=30m");
  });

  it("validates Discovery calendar fixture responses", async () => {
    const payload = { data: { kind: "ipos", window_days: 60, items: [], disclosure: "Illustrative calendar only." }, status: "ok", source: "synthetic-fixtures", freshness: "simulated", missing_fields: [], warnings: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 })));
    expect((await fetchDiscoveryCalendar("ipos", 60)).data?.kind).toBe("ipos");
  });

  it("preserves Watchlist symbols and validates Python summary fields", async () => {
    const payload = { data: { symbols: ["NVDA"], summaries: [{ symbol: "NVDA", name: "NVIDIA Corporation", sector: "Technology", industry: "Semiconductors", sample_close: 142.68, sample_change_percent: 1.4, technical_rating: "Hold", trend_state: "Mixed" }], disclosure: "Synthetic only." }, status: "ok", source: "python-engine-snapshot", freshness: "simulated", missing_fields: [], warnings: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    expect((await fetchWatchlistSummaries(["NVDA"])).data?.summaries[0]?.sample_close).toBe(142.68);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("symbols=NVDA");
  });

  it("stops requests at the configured timeout with a safe user message", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    })));
    const result = fetchOverview();
    const assertion = expect(result).rejects.toMatchObject({ message: "The local API timed out. Confirm that the demo service is running.", status: "failed" });
    await vi.advanceTimersByTimeAsync(5_000);
    await assertion;
  }, 10_000);
});
