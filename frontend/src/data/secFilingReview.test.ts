import { beforeEach, describe, expect, it, vi } from "vitest";
import { accessionsNewSinceReview, markSuccessfulFilingsReviewed, readSecFilingReviewSnapshot, writeSecFilingReviewSnapshot } from "./secFilingReview";
import { fetchSecWatchlistActivity, type SecWatchlistActivityEntry } from "./apiClient";

beforeEach(() => {
  window.sessionStorage.clear();
});

describe("SEC filing review snapshots", () => {
  it("stores review state in session storage and scopes it by session identity", () => {
    const snapshot = { version: 1 as const, issuers: { "0000320193": { accessions: ["a1"], reviewed_at: "2026-11-18T12:00:00Z" } } };
    expect(writeSecFilingReviewSnapshot("guest", snapshot)).toBe(true);
    expect(readSecFilingReviewSnapshot("guest")).toEqual(snapshot);
    expect(readSecFilingReviewSnapshot("account:user-2")).toBeNull();
  });

  it("does not call first-time filings new and compares later filings by accession identity", () => {
    const rows = ["a2", "a1"];
    expect(accessionsNewSinceReview(null, "0000320193", rows)).toBeNull();
    const snapshot = { version: 1 as const, issuers: { "0000320193": { accessions: ["a1"], reviewed_at: "2026-11-18T12:00:00Z" } } };
    expect(Array.from(accessionsNewSinceReview(snapshot, "0000320193", rows) ?? [])).toEqual(["a2"]);
  });

  it("marks only fully successful issuers reviewed and preserves failed issuers", () => {
    const old = { version: 1 as const, issuers: { "0000789019": { accessions: ["old"], reviewed_at: "2026-11-01T12:00:00Z" } } };
    const success: SecWatchlistActivityEntry = {
      requested_ticker: "AAPL", requested_exchange: "Nasdaq", status: "ok", error: null, warnings: [],
      data: { ticker: "AAPL", company_name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq", sic: null, sic_description: null, filings: [
        { cik: "0000320193", ticker: "AAPL", company_name: "Apple Inc.", exchange: "Nasdaq", sic: null, sic_description: null, form: "10-K/A", filing_date: "2026-11-18", report_date: null, accession_number: "new", primary_document: null, filing_url: null, items: null },
      ], forms: ["10-K"], disclosure: "Filed records." },
    };
    const failed: SecWatchlistActivityEntry = { requested_ticker: "MSFT", requested_exchange: "Nasdaq", status: "unavailable", data: null, error: "Unavailable", warnings: [] };
    const next = markSuccessfulFilingsReviewed(old, [success, failed], "2026-11-18T13:00:00Z");
    expect(next.issuers["0000320193"]).toEqual({ accessions: ["new"], reviewed_at: "2026-11-18T13:00:00Z" });
    expect(next.issuers["0000789019"]).toEqual(old.issuers["0000789019"]);
  });

  it("validates the bounded SEC batch request and issuer response association", async () => {
    const data = {
      entries: [{
        requested_ticker: "AAPL", requested_exchange: "Nasdaq", status: "ok", error: null, warnings: [],
        data: { ticker: "AAPL", company_name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq", sic: null, sic_description: null, filings: [], forms: ["10-K", "10-Q", "8-K"], disclosure: "Filed records." },
      }],
      limit: 5, disclosure: "Factual filing records.",
    };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      data, status: "ok", source: "sec-edgar", freshness: "live", provenance: "Official SEC EDGAR issuer submissions", warnings: [], missing_fields: [],
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await fetchSecWatchlistActivity([{ ticker: "AAPL", exchange: "Nasdaq" }]);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/discovery/filings/watchlist");
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({ companies: [{ ticker: "AAPL", exchange: "Nasdaq" }] });
    await expect(fetchSecWatchlistActivity([])).rejects.toMatchObject({ status: "invalid" });
  });
});
