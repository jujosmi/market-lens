import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { WatchlistFilingActivity } from "./WatchlistFilingActivity";

const aapl = {
  ticker: "AAPL", company_name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq", sic: "3571", sic_description: "Electronic Computers",
  forms: ["10-K", "10-Q", "8-K"], disclosure: "Official filing records only.",
};

function filing(accession: string, form = "10-Q") {
  return {
    cik: aapl.cik, ticker: "AAPL", company_name: aapl.company_name, exchange: "Nasdaq", sic: "3571",
    sic_description: "Electronic Computers", form, filing_date: "2026-11-18", report_date: "2026-10-31",
    accession_number: accession, primary_document: "current.htm",
    filing_url: "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/current.htm",
    items: form === "8-K" ? "2.02, 9.01" : null,
    acceptance_datetime: "2026-11-18T15:30:00Z",
    primary_doc_description: form.endsWith("/A") ? "Amended report" : "Quarterly report",
  };
}

function envelope(entries: unknown[], status = "ok") {
  return {
    data: { entries, limit: 5, disclosure: "Factual filing records." },
    status, source: "sec-edgar", freshness: "live", provenance: "LOCAL ACCEPTANCE MOCK",
    as_of: "2026-11-18T15:31:00Z", warnings: [], missing_fields: [],
  };
}

function okEntry(filings: unknown[], ticker = "AAPL", company = aapl) {
  return {
    requested_ticker: ticker, requested_exchange: company.exchange, status: "ok", data: { ...company, filings }, error: null, warnings: [],
  };
}

function mount(companies: { ticker: string; exchange: string | null }[] = [{ ticker: "AAPL", exchange: "Nasdaq" }]) {
  return render(<WatchlistFilingActivity companies={companies} reviewScope="guest" onSelectTicker={vi.fn()} onNavigate={vi.fn()} />);
}

beforeEach(() => {
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Watchlist Filing Activity", () => {
  it("shows first-time history without a new-since-review claim and marks an explicit snapshot", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope([okEntry([filing("0000320193-26-000001")])])), { status: 200 })));
    mount();
    expect(await screen.findByText("Initial history · not yet reviewed")).toBeInTheDocument();
    expect(screen.getByText(/LOCAL ACCEPTANCE MOCK/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View SEC filing" })).toHaveAttribute("href", "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/current.htm");
    expect(screen.queryByText(/NEW SINCE REVIEW/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mark successful companies reviewed" }));
    expect(await screen.findByText("No new accessions")).toBeInTheDocument();
    expect(Object.keys(window.sessionStorage).some((key) => key.includes("jujosmi_trade_sec_filing_review_v1"))).toBe(true);
  });

  it("identifies only accessions absent from the previous explicit review and keeps them after refresh", async () => {
    window.sessionStorage.setItem("jujosmi_trade_sec_filing_review_v1:guest", JSON.stringify({
      version: 1, issuers: { "0000320193": { accessions: ["0000320193-26-000001"], reviewed_at: "2026-11-17T12:00:00Z" } },
    }));
    const result = envelope([okEntry([filing("0000320193-26-000002", "10-K/A"), filing("0000320193-26-000001", "10-K")])]);
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(result), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(result), { status: 200 })));
    mount();
    expect(await screen.findByText("1 new since review")).toBeInTheDocument();
    expect(screen.getByText("NEW SINCE REVIEW")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Refresh filings" }));
    expect(await screen.findByText("1 new since review")).toBeInTheDocument();
  });

  it("filters amendments with their base filing form and preserves company navigation identity", async () => {
    const nav = vi.fn();
    const select = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope([okEntry([filing("0000320193-26-000002", "10-K/A")])])), { status: 200 })));
    render(<WatchlistFilingActivity companies={[{ ticker: "AAPL", exchange: "Nasdaq" }]} reviewScope="guest" onSelectTicker={select} onNavigate={nav} />);
    await screen.findByText("Amended report");
    fireEvent.change(screen.getByRole("combobox", { name: "Filter filing type" }), { target: { value: "10-K" } });
    expect(await screen.findByText("Amended report")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Company Research" }));
    expect(select).toHaveBeenCalledWith("AAPL", "Nasdaq");
    expect(nav).toHaveBeenCalledWith("research");
  });

  it("keeps a successful issuer available when another issuer is unavailable", async () => {
    const msft = { requested_ticker: "MSFT", requested_exchange: "Nasdaq", status: "rate_limited", data: null, error: "SEC request limit reached.", warnings: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope([okEntry([filing("0000320193-26-000001")]), msft], "partial")), { status: 200 })));
    mount([{ ticker: "AAPL", exchange: "Nasdaq" }, { ticker: "MSFT", exchange: "Nasdaq" }]);
    expect(await screen.findByText("Apple Inc.", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByText("SEC request limit reached.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mark successful companies reviewed" }));
    const snapshot = JSON.parse(window.sessionStorage.getItem("jujosmi_trade_sec_filing_review_v1:guest") ?? "{}");
    expect(snapshot.issuers["0000320193"]).toBeDefined();
    expect(snapshot.issuers["0000789019"]).toBeUndefined();
  });

  it("aborts stale activity requests when the saved company set changes", async () => {
    let resolveFirst: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveFirst = resolve; }))
      .mockResolvedValueOnce(new Response(JSON.stringify(envelope([{
        requested_ticker: "MSFT", requested_exchange: "Nasdaq", status: "ok",
        data: { ...aapl, ticker: "MSFT", company_name: "Microsoft Corporation", cik: "0000789019", filings: [] }, error: null, warnings: [],
      }])), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const view = mount();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    view.rerender(<WatchlistFilingActivity companies={[{ ticker: "MSFT", exchange: "Nasdaq" }]} reviewScope="guest" onSelectTicker={vi.fn()} onNavigate={vi.fn()} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    resolveFirst?.(new Response(JSON.stringify(envelope([okEntry([filing("stale")])])), { status: 200 }));
    expect(await screen.findByText("Microsoft Corporation", { selector: "h3" })).toBeInTheDocument();
    expect(screen.queryByText("Apple Inc.", { selector: "h3" })).not.toBeInTheDocument();
  });
});
