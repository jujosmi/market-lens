import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, fetchChart, fetchDiscovery, fetchDiscoveryCalendar, fetchOverview, fetchSecDirectory, fetchSecFilings, fetchSecIndustryCompanies, fetchSecResearch, fetchWatchlistSummaries } from "./apiClient";

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

  it("validates the limited SEC SIC browser contract and encodes its query", async () => {
    const payload = { data: { companies: [{ ticker: "AAPL", name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq", sic: "3571", sic_description: "Electronic Computers", sic_sector: "Manufacturing" }], total_matches: 1, total_candidates: 1, limit: 10, offset: 0, query: "Apple & Co", exchange: null, available_exchanges: ["Nasdaq"], classified_count: 1, unclassified_count: 0, disclosure: "Partial SEC SIC coverage." }, status: "ok", source: "sec-edgar", freshness: "cached", warnings: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await fetchSecIndustryCompanies({ query: "Apple & Co", limit: 10, offset: 0 });
    expect(response.data?.companies[0]?.sic_sector).toBe("Manufacturing");
    const requested = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(requested.pathname).toContain("/discovery/industry-companies");
    expect(requested.searchParams.get("q")).toBe("Apple & Co");
    expect(requested.searchParams.get("limit")).toBe("10");
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

  it("validates SEC directory records and sends bounded search, exchange, and pagination", async () => {
    const data = { companies: [{ ticker: "AAPL", name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq" }], total: 1, limit: 25, offset: 25, query: "Apple", exchange: "Nasdaq", available_exchanges: ["Nasdaq"], disclosure: "SEC source; not a complete inventory." };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data, status: "ok", source: "sec-edgar", freshness: "cached", warnings: [], missing_fields: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await fetchSecDirectory({ query: "Apple", exchange: "Nasdaq", limit: 25, offset: 25 });
    expect(response.data?.companies[0]).toMatchObject({ ticker: "AAPL", cik: "0000320193" });
    const request = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(request.pathname).toContain("/discovery/companies");
    expect(request.searchParams).toMatchObject({});
    expect(request.searchParams.get("q")).toBe("Apple");
    expect(request.searchParams.get("exchange")).toBe("Nasdaq");
    expect(request.searchParams.get("limit")).toBe("25");
    expect(request.searchParams.get("offset")).toBe("25");
  });

  it("validates SEC filing identity, accession, dates, and official document link", async () => {
    const data = { ticker: "AAPL", company_name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq", sic: "3571", sic_description: "Electronic Computers", forms: ["10-K", "10-Q", "8-K", "S-1"], filings: [{ cik: "0000320193", ticker: "AAPL", company_name: "Apple Inc.", exchange: "Nasdaq", sic: "3571", sic_description: "Electronic Computers", form: "10-Q", filing_date: "2026-10-30", report_date: "2026-09-27", accession_number: "0000320193-26-000001", primary_document: "quarter.htm", filing_url: "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/quarter.htm" }], disclosure: "Filed records only." };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data, status: "ok", source: "sec-edgar", freshness: "live", warnings: [], missing_fields: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await fetchSecFilings("AAPL", "Nasdaq");
    expect(response.data?.filings[0]?.accession_number).toBe("0000320193-26-000001");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/discovery/filings/AAPL?exchange=Nasdaq");
  });

  it("passes an SEC exchange qualifier through to Company Research", async () => {
    const data = { identity: { cik: "0000100001", ticker: "EXM", name: "Example Holdings", exchange: "NYSE", identity_source: "sec_company_tickers" }, facts: [], filings: [], missing_fields: ["revenue"], source: "SEC EDGAR submissions and Company Facts", live_data: true, status: "partial", as_of: "2026-11-17T12:00:00Z", warnings: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data, status: "partial", source: "sec-edgar", freshness: "live", warnings: [], missing_fields: data.missing_fields }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchSecResearch("EXM", undefined, "NYSE");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/companies/EXM/sec-research?exchange=NYSE");
  });

  it("validates annual and quarterly statement periods without dropping provenance", async () => {
    const metric = { field: "revenue", taxonomy: "us-gaap", tag: "Revenues", label: "Revenue", value: 100, original_value: "100", unit: "USD", currency: "USD", period_start: "2025-01-01", period_end: "2025-12-31", duration_days: 365, form: "10-K", filed: "2026-02-01", accession_number: "0000000001-26-000001", filing_url: "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/a.htm", comparison_percent: null, comparison_period_end: null };
    const period = { fiscal_year: 2025, fiscal_period: "FY", period_type: "annual", period_start: "2025-01-01", period_end: "2025-12-31", metrics: { revenue: [metric] } };
    const data = { identity: { cik: "0000000001", ticker: "EXM", name: "Example Holdings", exchange: null, identity_source: "sec_company_tickers" }, facts: [], annual_periods: [period], quarterly_periods: [], ytd_periods: [], filings: [], missing_fields: [], source: "SEC EDGAR", live_data: true, status: "ok", as_of: "2026-11-18T12:00:00Z", warnings: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ data, status: "ok", source: "sec-edgar", freshness: "live", warnings: [], missing_fields: [] }), { status: 200 })));
    const report = await fetchSecResearch("EXM");
    expect(report.data?.annual_periods?.[0]?.metrics.revenue?.[0]).toMatchObject({ original_value: "100", unit: "USD", tag: "Revenues" });
  });

  it("rejects financial statement rows with missing SEC filing provenance", async () => {
    const data = { identity: { cik: "0000000001", ticker: "EXM", name: "Example Holdings", exchange: null, identity_source: "sec_company_tickers" }, facts: [], annual_periods: [{ fiscal_year: 2025, fiscal_period: "FY", period_type: "annual", period_end: "2025-12-31", metrics: { revenue: [{ original_value: "100", unit: "USD", tag: "Revenues", form: "10-K", filed: "2026-02-01", period_end: "2025-12-31", filing_url: null }] } }], quarterly_periods: [], ytd_periods: [], filings: [], missing_fields: [], source: "SEC EDGAR", live_data: true, status: "ok", as_of: "2026-11-18T12:00:00Z", warnings: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ data, status: "ok", source: "sec-edgar", freshness: "live", warnings: [], missing_fields: [] }), { status: 200 })));
    await expect(fetchSecResearch("EXM")).rejects.toMatchObject({ message: "The local API data did not match the expected response shape.", status: "failed" });
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
