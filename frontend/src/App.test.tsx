import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { buildSeries } from "./data/fixtures";

function renderDevelopmentApp() {
  const result = render(<App />);
  fireEvent.change(screen.getByRole('combobox', { name: 'Data mode' }), { target: { value: 'fixtures' } });
  return result;
}

afterEach(() => {
  window.history.replaceState({}, "", "/");
  window.sessionStorage.clear();
  window.localStorage.clear();
  vi.unstubAllGlobals();
});

describe("Jujosmi Trade UI 2.0 prototype", () => {
  it("shows the new logo and links top-left branding to Jujosmi.com in the current tab", () => {
    render(<App />);
    const brandLinks = screen.getAllByRole("link", { name: "Visit Jujosmi.com" });
    expect(brandLinks).toHaveLength(2);
    for (const link of brandLinks) {
      expect(link).toHaveAttribute("href", "https://jujosmi.com");
      expect(link).not.toHaveAttribute("target");
    }
    expect(screen.getByRole("img", { name: "Jujosmi Labs" })).toHaveAttribute("src", "/jujosmi-logo-simple-shadow.png");
  });

  it("defaults to a public view and embeds a branded TradingView chart without rendering fixture metrics", async () => {
    render(<App />);
    expect(screen.getByRole("combobox", { name: "Data mode" })).toHaveValue("public");
    expect(screen.getByText(/Jujosmi does not extract chart data/)).toBeInTheDocument();
    expect(screen.getByText("Market summary")).toBeInTheDocument();
    expect(screen.queryByText("$142.68")).not.toBeInTheDocument();
    await waitFor(() => expect(document.querySelector("script[src*='embed-widget-advanced-chart.js']")).toBeInTheDocument());
    const script = document.querySelector("script[src*='embed-widget-advanced-chart.js']");
    expect(JSON.parse(script?.textContent ?? "{}")).toMatchObject({ symbol: "NASDAQ:NVDA", theme: "dark", allow_symbol_change: true, autosize: true });
    expect(screen.getByRole("link", { name: "NASDAQ:NVDA chart" })).toHaveAttribute("href", "https://www.tradingview.com/symbols/NASDAQ-NVDA/");
  });

  it("keeps guest access when Supabase is not configured and never invents a signed-in session", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Account sign-in" }));
    expect(screen.getByText(/Account sign-in is disabled in this release/)).toBeInTheDocument();
    expect(screen.getByText("No account service is contacted and no session is created.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Market Overview" })).toBeInTheDocument();
  });

  it("reinitializes the TradingView widget with the selected exchange-qualified ticker", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.selectOptions(screen.getByRole("combobox", { name: "Selected chart ticker" }), "JPM");
    await waitFor(() => {
      const scripts = Array.from(document.querySelectorAll("script[src*='embed-widget-advanced-chart.js']"));
      expect(scripts.some((script) => JSON.parse(script.textContent ?? "{}").symbol === "NYSE:JPM")).toBe(true);
    });
    expect(screen.getByRole("heading", { name: "NYSE:JPM" })).toBeInTheDocument();
  });

  it("keeps Discovery, Company Research, and Watchlist navigable without synthetic public data", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Discovery" }));
    expect(await screen.findByRole("heading", { name: "Explore SEC company records." })).toBeInTheDocument();
    expect(screen.getByText(/not a complete or authoritative list of currently tradable securities/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    expect(await screen.findByText(/Identity loads from the official SEC directory/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Watchlist" }));
    expect(await screen.findByRole("heading", { name: "4 tickers" })).toBeInTheDocument();
    expect(screen.getAllByText("Quote and company research unavailable")).toHaveLength(4);
  });

  it("loads real-shaped SEC directory rows and navigates the selected issuer to public research", async () => {
    const directory = { companies: [{ ticker: "AAPL", name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq" }], total: 1, limit: 25, offset: 0, query: "", exchange: null, available_exchanges: ["Nasdaq"], disclosure: "SEC association file; not a complete inventory." };
    const report = { identity: { cik: "0000320193", ticker: "AAPL", name: "Apple Inc.", exchange: "Nasdaq", identity_source: "sec_company_tickers" }, facts: [], filings: [], missing_fields: ["revenue"], source: "SEC EDGAR submissions and Company Facts", live_data: true, status: "partial", as_of: "2026-11-17T12:00:00Z", warnings: ["No supported facts were available."] };
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const payload = url.includes("/discovery/companies")
        ? { data: directory, status: "ok", source: "sec-edgar", freshness: "live", warnings: [], missing_fields: [] }
        : { data: report, status: "partial", source: "sec-edgar", freshness: "cached", warnings: report.warnings, missing_fields: report.missing_fields };
      return Promise.resolve(new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Discovery" }));
    expect(await screen.findByRole("button", { name: "Open Company Research for Apple Inc. (AAPL)" })).toBeInTheDocument();
    expect(screen.getByText("0000320193")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open Company Research for Apple Inc. (AAPL)" }));
    expect(await screen.findByRole("heading", { name: /Apple Inc\./ })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/companies/AAPL/sec-research?exchange=Nasdaq"))).toBe(true);
  });

  it("loads selected-company filing history with SEC dates and links in public Discovery", async () => {
    const directory = { companies: [{ ticker: "AAPL", name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq" }], total: 1, limit: 25, offset: 0, query: "", exchange: null, available_exchanges: ["Nasdaq"], disclosure: "SEC association file; not exhaustive." };
    const filings = { ticker: "AAPL", company_name: "Apple Inc.", cik: "0000320193", exchange: "Nasdaq", sic: "3571", sic_description: "Electronic Computers", forms: ["10-K", "10-Q", "8-K", "S-1"], filings: [{ cik: "0000320193", ticker: "AAPL", company_name: "Apple Inc.", exchange: "Nasdaq", sic: "3571", sic_description: "Electronic Computers", form: "10-Q", filing_date: "2026-10-30", report_date: "2026-09-27", accession_number: "0000320193-26-000001", primary_document: "quarter.htm", filing_url: "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/quarter.htm" }], disclosure: "Filings are not scheduled events." };
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url=String(input); const payload=url.includes("/discovery/companies")
        ? {data:directory,status:"ok",source:"sec-edgar",freshness:"live",warnings:[],missing_fields:[]}
        : {data:filings,status:"ok",source:"sec-edgar",freshness:"live",warnings:[],missing_fields:[]};
      return Promise.resolve(new Response(JSON.stringify(payload),{status:200,headers:{"Content-Type":"application/json"}}));
    });
    vi.stubGlobal("fetch",fetchMock);
    const user=userEvent.setup();render(<App />);await user.click(screen.getByRole("button",{name:"Discovery"}));
    await user.click(await screen.findByRole("button",{name:"Recent filings"}));
    expect(await screen.findByText("Accession 0000320193-26-000001")).toBeInTheDocument();
    expect(screen.getByRole("link",{name:/Open filing/})).toHaveAttribute("href",filings.filings[0]?.filing_url);
    expect(screen.getByText(/Electronic Computers/)).toBeInTheDocument();
  });

  it("shows public SEC Events & Filings and classifies only filing items explicitly supplied by SEC", async () => {
    const report = { identity: { cik: "0001045810", ticker: "NVDA", name: "NVIDIA Corporation", exchange: "Nasdaq", identity_source: "sec_company_tickers" }, facts: [], annual_periods: [], quarterly_periods: [], ytd_periods: [], filings: [], missing_fields: [], source: "SEC EDGAR", live_data: true, status: "partial", as_of: "2026-11-18T12:00:00Z", warnings: [] };
    const filingData = { ticker: "NVDA", company_name: "NVIDIA Corporation", cik: "0001045810", exchange: "Nasdaq", sic: null, sic_description: null, forms: ["8-K", "10-Q"], disclosure: "SEC filed documents.", filings: [
      { cik: "0001045810", ticker: "NVDA", company_name: "NVIDIA Corporation", exchange: "Nasdaq", sic: null, sic_description: null, form: "8-K", filing_date: "2026-11-17", report_date: "2026-11-16", accession_number: "0001045810-26-000001", primary_document: "current.htm", filing_url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/current.htm", items: "2.02, 9.01" },
      { cik: "0001045810", ticker: "NVDA", company_name: "NVIDIA Corporation", exchange: "Nasdaq", sic: null, sic_description: null, form: "8-K", filing_date: "2026-11-16", report_date: null, accession_number: "0001045810-26-000002", primary_document: "current2.htm", filing_url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000002/current2.htm", items: null },
      { cik: "0001045810", ticker: "NVDA", company_name: "NVIDIA Corporation", exchange: "Nasdaq", sic: null, sic_description: null, form: "8-K", filing_date: "2026-11-15", report_date: null, accession_number: "0001045810-26-000003", primary_document: "current3.htm", filing_url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000003/current3.htm", items: "5.02" },
    ] };
    vi.stubGlobal("fetch", vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const data = url.includes("/discovery/filings/") ? filingData : report;
      return Promise.resolve(new Response(JSON.stringify({ data, status: "partial", source: "sec-edgar", freshness: "cached", as_of: "2026-11-18T12:00:00Z", missing_fields: [], warnings: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    }));
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    await user.click(screen.getByRole("tab", { name: "Events & Filings" }));
    expect(await screen.findByText("Results of operations and financial condition · Item 2.02")).toBeInTheDocument();
    expect(screen.getByText("Current report · item metadata unavailable")).toBeInTheDocument();
    expect(screen.getByText("Departure, election, or appointment of certain officers · Item 5.02")).toBeInTheDocument();
    expect(screen.getByText("Filing date: 2026-11-17 · Report date: 2026-11-16")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open source filing" })[0]).toHaveAttribute("href", expect.stringContaining("sec.gov/Archives"));
    expect(screen.queryByText(/Analyst expectations/)).not.toBeInTheDocument();
  });

  it("provides company-specific provider-hosted news and technical links instead of empty public tabs", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    await user.click(screen.getByRole("tab", { name: "News" }));
    expect(screen.getByRole("link", { name: /Open company news at TradingView/ })).toHaveAttribute("href", "https://www.tradingview.com/symbols/NASDAQ-NVDA/news/");
    expect(screen.getByText(/does not copy headlines, add sentiment labels/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Technical" }));
    expect(screen.getByRole("link", { name: /Open technical analysis at TradingView/ })).toHaveAttribute("href", "https://www.tradingview.com/symbols/NASDAQ-NVDA/technicals/");
    expect(screen.getByText(/does not extract indicators/)).toBeInTheDocument();
  });

  it("does not let a slow previous SEC response replace the newly selected company's research", async () => {
    const pending: { symbol: string; resolve: (response: Response) => void }[] = [];
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => new Promise<Response>((resolve) => {
      const match = String(input).match(/\/companies\/([A-Z]+)\/sec-research/);
      if (match) pending.push({ symbol: match[1]!, resolve });
      else resolve(new Response("{}", { status: 404 }));
    }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    await waitFor(() => expect(pending.some((item) => item.symbol === "NVDA")).toBe(true));
    await user.click(screen.getByRole("button", { name: "Market Overview" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Selected chart ticker" }), "AAPL");
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    await waitFor(() => expect(pending.some((item) => item.symbol === "AAPL")).toBe(true));
    const report = (ticker: string, name: string, cik: string) => ({ data: { identity: { cik, ticker, name, exchange: "Nasdaq", identity_source: "sec_company_tickers" }, facts: [], filings: [], annual_periods: [], quarterly_periods: [], ytd_periods: [], missing_fields: [], source: "SEC EDGAR", live_data: true, status: "partial", as_of: "2026-11-18T12:00:00Z", warnings: [] }, status: "partial", source: "sec-edgar", freshness: "cached", missing_fields: [], warnings: [] });
    const respond = async (symbol: string, name: string, cik: string) => {
      await act(async () => pending.find((item) => item.symbol === symbol)!.resolve(new Response(JSON.stringify(report(symbol, name, cik)), { status: 200, headers: { "Content-Type": "application/json" } })));
    };
    await respond("AAPL", "Apple Inc.", "0000320193");
    expect(await screen.findByRole("heading", { name: /Apple Inc\./ })).toBeInTheDocument();
    await respond("NVDA", "NVIDIA Corporation", "0001045810");
    expect(screen.getByRole("heading", { name: /Apple Inc\./ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /NVIDIA Corporation/ })).not.toBeInTheDocument();
  });

  it("renders SEC-sourced issuer identity, original fact values, and filing provenance in public research", async () => {
    const fact = { field: "revenue", taxonomy: "us-gaap", tag: "RevenueFromContractWithCustomerExcludingAssessedTax", label: "Revenue", value: 123456, original_value: "123456.00", unit: "USD", currency: "USD", period_start: "2025-10-01", period_end: "2025-12-31", fiscal_year: 2025, fiscal_period: "Q4", form: "10-Q", filed: "2026-02-01", accession_number: "0001045810-26-000001", filing_url: "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/q.htm", latest_reported_version: true };
    const data = { identity: { cik: "0001045810", ticker: "NVDA", name: "NVIDIA Corporation", exchange: "Nasdaq", identity_source: "sec_company_tickers" }, facts: [fact], filings: [{ cik: "0001045810", accession_number: fact.accession_number, form: "10-Q", filing_date: "2026-02-01", report_period: "2025-12-31", primary_document: "q.htm", filing_url: fact.filing_url }], missing_fields: ["net_income"], source: "SEC EDGAR submissions and Company Facts", live_data: true, status: "partial", as_of: "2026-02-02T12:00:00Z", warnings: ["One standard field is not reported."] };
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ data, status: "partial", source: "sec-edgar", freshness: "live", as_of: data.as_of, provenance: "Official SEC EDGAR", missing_fields: data.missing_fields, warnings: data.warnings }), { status: 200, headers: { "Content-Type": "application/json" } })));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await user.selectOptions(screen.getByRole("combobox", { name: "Selected chart ticker" }), "NVDA");
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    expect(await screen.findByRole("heading", { name: /NVIDIA Corporation/ })).toBeInTheDocument();
    expect(screen.getByText("123456.00 USD")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Company facts & latest filings" })).toBeInTheDocument();
    expect(screen.getByText(/Source: U.S. Securities and Exchange Commission EDGAR/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open filing" })).toHaveAttribute("href", fact.filing_url);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/companies/NVDA/sec-research"), expect.objectContaining({ method: "GET" }));
    await user.click(screen.getByRole("tab", { name: "Financials" }));
    expect(await screen.findByRole("region", { name: "SEC reported financial facts" })).toBeInTheDocument();
    expect(screen.getByText("Latest reported version")).toBeInTheDocument();
  });

  it("labels the dashboard as fixture data, never live quotes", () => {
    renderDevelopmentApp();
    expect(screen.getByText(/Every price and metric on this screen is illustrative fixture data/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /NVDA 1M illustrative chart, area style/i })).toBeInTheDocument();
    expect(screen.getByText("+1.84%", { selector: ".price-change" })).toBeInTheDocument();
    expect(screen.queryByText("NaN%", { selector: ".price-change" })).not.toBeInTheDocument();
  });

  it("filters fixture-backed tickers and updates the selected company", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.type(screen.getByRole("textbox", { name: /search ticker or company/i }), "MSF");
    await user.click(screen.getByRole("option", { name: /MSFT/ }));
    expect(screen.getByRole("heading", { name: "Microsoft Corporation" })).toBeInTheDocument();
    expect(screen.getByText("MSFT", { selector: ".stock-symbol" })).toBeInTheDocument();
  });

  it("switches chart range and rendering style using local fixtures", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByRole("button", { name: "1Y" }));
    expect(screen.getByRole("img", { name: /NVDA 1Y illustrative chart/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Line" }));
    expect(screen.getByRole("img", { name: /NVDA 1Y illustrative chart, line style/i })).toBeInTheDocument();
  });

  it("offers interval selection and forwards the selected interval to FastAPI", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const data = url.includes("/chart?")
        ? { symbol: "NVDA", range: "1M", interval: new URL(url).searchParams.get("interval"), bars: [{ time: "SAMPLE+001", open: 142, high: 145, low: 141, close: 144, volume: 100 }], label: "Python synthetic interpolation, not historical market data" }
        : url.endsWith("/analysis")
          ? { symbol: "NVDA", name: "NVIDIA Corporation", indicators: { last: 144, change: 1.1 }, move_source: "synthetic", trend_state: "Mixed", rating: "Hold", rating_source: "Python", technical_rating: "Hold", analyst_rating: null, analyst_count: 0, analyst_score: null, analyst_period: null, constructive_checks: 1, caution_checks: 1, rating_checks_complete: true, rating_checks: [], returns: {}, observations: 320, hist_vol_observations: 319, drawdown_observations: 320, beta_observations: 300, as_of: "2025-12-31", disclosure: "Synthetic only." }
          : { markets: [], sector_activity: [], disclosure: "Synthetic only." };
      return Promise.resolve(new Response(JSON.stringify({ data, status: "ok", source: url.includes("/chart?") || url.endsWith("/analysis") ? "python-engine-snapshot" : "synthetic-fixtures", freshness: "simulated", missing_fields: [], warnings: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    await user.selectOptions(screen.getByRole("combobox", { name: "Chart interval" }), "30m");
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("interval=30m"))).toBe(true));
  });

  it("keeps each illustrative chart aligned with its sample close", () => {
    const points = buildSeries([3, 8, 4, 10], "1M", 142.68);
    expect(points.at(-1)).toBe(142.68);
    expect(Math.max(...points) - Math.min(...points)).toBeLessThan(13);
  });

  it("previews loading, unavailable, and recoverable error states without fetching data", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByText("Preview response states"));
    await user.click(screen.getByRole("button", { name: "Loading" }));
    expect(screen.getByRole("status", { name: "Loading illustrative chart data" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Unavailable" }));
    expect(screen.getByText("No sample price history")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Error" }));
    expect(screen.getByRole("alert")).toHaveTextContent("No market request was made");
    await user.click(screen.getByRole("button", { name: "Retry preview" }));
    expect(screen.getByRole("img", { name: /NVDA 1M illustrative chart/i })).toBeInTheDocument();
  });

  it("opens a chart dialog and closes it with Escape", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByRole("button", { name: "Expand chart" }));
    expect(screen.getByRole("dialog", { name: "Expanded chart" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Expanded chart" })).not.toBeInTheDocument());
  });

  it("focuses ticker search with the Ctrl+K shortcut", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.keyboard("{Control>}k{/Control}");
    expect(screen.getByRole("textbox", { name: /search ticker or company/i })).toHaveFocus();
  });

  it("toggles the selected fixture in the prototype watchlist", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    const action = screen.getByRole("button", { name: /in watchlist/i });
    await user.click(action);
    expect(screen.getByRole("button", { name: /add to watchlist/i })).toHaveAttribute("aria-pressed", "false");
    await user.click(screen.getByRole("button", { name: /add to watchlist/i }));
    expect(screen.getByRole("button", { name: /in watchlist/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("navigates into the functional Discovery, Research, and Watchlist workspaces", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    const nav = screen.getByRole("navigation", { name: "Workspaces" });
    await user.click(within(nav).getByRole("button", { name: /Discovery/i }));
    expect(await screen.findByRole("heading", { name: "Explore the market." })).toBeInTheDocument();
    expect(await screen.findByRole("table", { name: "Simulated company directory" })).toBeInTheDocument();
    await user.click(within(nav).getByRole("button", { name: /Company Research/i }));
    expect(await screen.findByRole("heading", { name: "Business & valuation" })).toBeInTheDocument();
    await user.click(within(nav).getByRole("button", { name: "Watchlist" }));
    expect(await screen.findByRole("table", { name: "Session watchlist" })).toBeInTheDocument();
  });

  it("uses the API calendar view in FastAPI mode", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const data = url.includes("/discovery/calendar")
        ? { kind: "ipos", window_days: 60, items: [{ symbol: "SAMPLE1", name: "Example issuer", date_label: "Fixture date", title: "API IPO fixture", detail: "Not a real offering." }], disclosure: "Synthetic calendar fixtures only." }
        : url.endsWith("/discovery")
          ? { sectors: [], industries: [], companies: [], selected_sector: null, selected_industry: null, query: "", disclosure: "Synthetic directory." }
          : { markets: [], sector_activity: [], disclosure: "Synthetic." };
      return Promise.resolve(new Response(JSON.stringify({ data, status: "ok", source: "synthetic-fixtures", freshness: "simulated", missing_fields: [], warnings: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    const nav = screen.getByRole("navigation", { name: "Workspaces" });
    await user.click(within(nav).getByRole("button", { name: /Discovery/i }));
    await user.click(screen.getByRole("tab", { name: "IPO calendar" }));
    expect(await screen.findByText("API IPO fixture")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/discovery/calendar?kind=ipos"))).toBe(true);
  });

  it("renders Python-backed Watchlist summaries and avoids a frontend price fallback", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      let data: Record<string, unknown>;
      let source: "synthetic-fixtures" | "python-engine-snapshot" = "synthetic-fixtures";
      if (url.includes("/watchlist/summaries")) {
        source = "python-engine-snapshot";
        data = { symbols: ["NVDA", "AAPL", "MSFT", "AMZN"], summaries: ["NVDA", "AAPL", "MSFT", "AMZN"].map((symbol) => ({ symbol, name: symbol === "NVDA" ? "NVIDIA from Python" : symbol, sector: "Python sector", industry: "Python industry", sample_close: 999.25, sample_change_percent: 2.5, technical_rating: "Python Hold", trend_state: "Python trend" })), disclosure: "Python synthetic inputs." };
      } else if (url.endsWith("/analysis")) {
        source = "python-engine-snapshot";
        data = { symbol: "NVDA", name: "NVIDIA Corporation", indicators: { last: 999.25 }, move_source: "synthetic", trend_state: "Mixed", rating: "Hold", rating_source: "Python", technical_rating: "Hold", analyst_rating: null, analyst_count: 0, analyst_score: null, analyst_period: null, constructive_checks: 1, caution_checks: 1, rating_checks_complete: true, rating_checks: [], returns: {}, observations: 320, hist_vol_observations: 319, drawdown_observations: 320, beta_observations: 300, as_of: "2025-12-31", disclosure: "Synthetic only." };
      } else data = { markets: [], sector_activity: [], disclosure: "Synthetic only." };
      return Promise.resolve(new Response(JSON.stringify({ data, status: "ok", source, freshness: "simulated", missing_fields: [], warnings: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    fireEvent.change(screen.getByRole("combobox", { name: "Data mode" }), { target: { value: "fastapi" } });
    expect(screen.getByRole("combobox", { name: "Data mode" })).toHaveValue("fastapi");
    expect(screen.getByText("LOCAL API · SYNTHETIC")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Workspaces" });
    await user.click(within(nav).getByRole("button", { name: "Watchlist" }));
    expect(screen.getByText("LOCAL API · SYNTHETIC")).toBeInTheDocument();
    expect(screen.getByText("PYTHON SAMPLE CLOSE")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/watchlist/summaries"))).toBe(true));
    expect(await screen.findByText(/NVIDIA from Python · NASDAQ/)).toBeInTheDocument();
    expect(screen.getAllByText("$999.25").length).toBe(4);
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/watchlist/summaries"))).toBe(true);
  });

  it("shows an unavailable Watchlist state without falling back to static prices", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const payload = url.includes("/watchlist/summaries")
        ? { data: null, status: "unavailable", source: "python-engine-snapshot", freshness: "simulated", missing_fields: [], warnings: ["No synthetic summaries are available."] }
        : { data: { markets: [], sector_activity: [], disclosure: "Synthetic only." }, status: "ok", source: "synthetic-fixtures", freshness: "simulated", missing_fields: [], warnings: [] };
      return Promise.resolve(new Response(JSON.stringify(payload), { status: url.includes("/watchlist/summaries") ? 404 : 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    const nav = screen.getByRole("navigation", { name: "Workspaces" });
    await user.click(within(nav).getByRole("button", { name: "Watchlist" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No synthetic summaries are available.");
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.queryByText("$142.68")).not.toBeInTheDocument();
  });

  it("filters Discovery by sector and industry and selects a company for research", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    const nav = screen.getByRole("navigation", { name: "Workspaces" });
    await user.click(within(nav).getByRole("button", { name: "Discovery" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Filter sector" }), "Technology");
    await user.selectOptions(screen.getByRole("combobox", { name: "Filter industry" }), "Semiconductors");
    expect(screen.getByRole("heading", { name: "1 companies in view" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Research NVDA" }));
    expect(await screen.findByRole("heading", { name: /NVIDIA Corporation/ })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Business & valuation" })).toBeInTheDocument();
  });

  it("shows distinct Discovery loading and recoverable error states", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByRole("navigation", { name: "Workspaces" }).querySelector("button[aria-label='Discovery']") ?? screen.getByRole("button", { name: "Discovery" }));
    await user.click(screen.getByRole("button", { name: "Loading" }));
    expect(screen.getByRole("status")).toHaveTextContent("Loading illustrative directory");
    await user.click(screen.getByRole("button", { name: "Error" }));
    expect(screen.getByRole("alert")).toHaveTextContent("No provider request was made");
    await user.click(screen.getByRole("button", { name: "Try fixture again" }));
    expect(screen.getByRole("table", { name: "Simulated company directory" })).toBeInTheDocument();
  });

  it("renders financial and analyst research panels and filters sample headlines", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    expect(screen.getAllByText("Revenue · TTM").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("tab", { name: "Analysts & events" }));
    expect(screen.getByText("Analyst expectations")).toBeInTheDocument();
    expect(screen.getByText("Earnings & events")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "News" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Filter headline sentiment" }), "Neutral");
    expect(screen.getAllByText("Neutral").length).toBeGreaterThan(0);
    expect(screen.queryByText("Illustrative headline: analysts discuss long-term demand trends")).not.toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Technical" }));
    expect(screen.getByText("METHODOLOGY NOTE")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Error" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Sample research unavailable");
    await user.click(screen.getByRole("button", { name: "Try fixture again" }));
    expect(screen.getByText("Illustrative inputs only")).toBeInTheDocument();
  });

  it("adds, sorts, removes, and navigates from the session watchlist", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByRole("button", { name: "Watchlist" }));
    await screen.findByRole("table", { name: "Session watchlist" });
    await user.type(screen.getByRole("textbox", { name: "Search tickers to add" }), "GOOGL");
    await user.click(screen.getByRole("option", { name: /GOOGL/ }));
    expect(screen.getByRole("status")).toHaveTextContent("GOOGL added to this browser-session watchlist");
    const table = screen.getByRole("table", { name: "Session watchlist" });
    expect(table).toHaveTextContent("GOOGL");
    await user.selectOptions(screen.getByRole("combobox", { name: "Sort watchlist" }), "Daily move");
    const rows = within(table).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("NVDA");
    expect(rows[2]).toHaveTextContent("AMZN");
    await user.click(screen.getByRole("button", { name: /Research GOOGL/ }));
    expect(await screen.findByRole("heading", { name: /Alphabet Inc./ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Watchlist" }));
    await user.click(screen.getByRole("button", { name: "Remove GOOGL from NASDAQ watchlist entry" }));
    expect(screen.getByRole("table", { name: "Session watchlist" })).not.toHaveTextContent("GOOGL");
  });

  it("restores the temporary guest watchlist after an app reload", async () => {
    const user = userEvent.setup();
    const firstRender = renderDevelopmentApp();
    await user.click(screen.getByRole("button", { name: "Watchlist" }));
    await user.type(screen.getByRole("textbox", { name: "Search tickers to add" }), "GOOGL");
    await user.click(screen.getByRole("option", { name: /GOOGL/ }));
    expect(window.sessionStorage.getItem("jujosmi_trade_guest_watchlist_v1")).toContain("GOOGL");

    firstRender.unmount();
    window.history.replaceState({}, "", "/");
    render(<App />);
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fixtures");
    await user.click(screen.getByRole("button", { name: "Watchlist" }));
    expect(screen.getByRole("table", { name: "Session watchlist" })).toHaveTextContent("GOOGL");
  });

  it("switches Discovery into earnings and IPO fixture calendars", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByRole("button", { name: "Discovery" }));
    await user.click(screen.getByRole("tab", { name: "Industry directory" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("heading", { name: "Upcoming earnings fixtures" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Earnings soon" })).toHaveFocus();
    expect(screen.getByText("Quarterly earnings call")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "IPO calendar" }));
    expect(screen.getByRole("heading", { name: "IPO calendar fixtures" })).toBeInTheDocument();
    expect(screen.getByText("Example public listing")).toBeInTheDocument();
  });

  it("opens the welcome landing and enters a directly routable terminal workspace", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/welcome");
    render(<App />);
    expect(screen.getByRole("heading", { name: /Jujosmi Trade/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Visit Jujosmi.com" })).toHaveAttribute("href", "https://jujosmi.com");
    await user.click(screen.getByRole("button", { name: "Enter Jujosmi Trade" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Data mode" }), { target: { value: "fixtures" } });
    expect(window.location.pathname).toBe("/market-overview");
    expect(screen.getByRole("heading", { name: /Good morning/ })).toBeInTheDocument();
  });

  it("supports keyboard activation of the landing action", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/welcome");
    const first = render(<App />);
    const enter = screen.getByRole("button", { name: "Enter Jujosmi Trade" });
    enter.focus();
    await user.keyboard("{Enter}");
    expect(window.location.pathname).toBe("/market-overview");
    expect(screen.getByRole("heading", { name: "Market summary" })).toBeInTheDocument();
    first.unmount();
    window.history.replaceState({}, "", "/welcome");
    render(<App />);
    screen.getByRole("button", { name: "Enter Jujosmi Trade" }).focus();
    await user.keyboard(" ");
    expect(window.location.pathname).toBe("/market-overview");
    expect(screen.getByRole("heading", { name: "Market summary" })).toBeInTheDocument();
  });

  it("loads a bookmarked workspace route directly", async () => {
    window.history.replaceState({}, "", "/watchlist");
    renderDevelopmentApp();
    expect(await screen.findByRole("heading", { name: "Keep your research close." })).toBeInTheDocument();
    expect(await screen.findByRole("table", { name: "Session watchlist" })).toBeInTheDocument();
  });

  it("opens a simulated Discovery preview and routes its action into Company Research", async () => {
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.click(screen.getByRole("button", { name: "Discovery" }));
    await user.click(screen.getByRole("button", { name: "Show sample details for NVDA, NVIDIA Corporation" }));
    const dialog = screen.getByRole("dialog", { name: "NVDA · NVIDIA Corporation" });
    expect(within(dialog).getByText("Semiconductors")).toBeInTheDocument();
    expect(within(dialog).getByText(/simulated demonstration fixtures/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Open Company Research" }));
    expect(await screen.findByRole("heading", { name: "Business & valuation" })).toBeInTheDocument();
  });

  it("renders local FastAPI overview data when demonstration mode is selected", async () => {
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const data = url.includes("/watchlist/summaries")
        ? { symbols: ["NVDA", "AAPL", "MSFT", "AMZN"], summaries: ["NVDA", "AAPL", "MSFT", "AMZN"].map((symbol) => ({ symbol, name: `${symbol} API`, sector: "API sector", industry: "API industry", sample_close: 999, sample_change_percent: 1, technical_rating: "Hold", trend_state: "Mixed" })), disclosure: "Synthetic." }
        : { markets: [{ name: "Demo Index", symbol: "DIX", value: "123.45", change: "+0.50%", tone: "up", series: [1, 2, 3] }], sector_activity: [{ name: "Demo sector", value: 66 }], disclosure: "Synthetic demonstration data only; not live." };
      const source = url.includes("/watchlist/summaries") ? "python-engine-snapshot" : "synthetic-fixtures";
      return Promise.resolve(new Response(JSON.stringify({ data, status: "ok", source, freshness: "simulated", warnings: [], missing_fields: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    expect(await screen.findByText("Demo Index")).toBeInTheDocument();
    expect(await screen.findByText("Demo sector")).toBeInTheDocument();
    expect(await screen.findAllByText("$999.00")).toHaveLength(4);
    expect(await screen.findByText("Synthetic demonstration data only; not live.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/overview"), expect.objectContaining({ method: "GET" }));
  });

  it("requests Discovery filters from the FastAPI demo and renders synthetic listings", async () => {
    const discovery = { sectors: ["Technology"], industries: [{ name: "Semiconductors", sector: "Technology", company_count: 1 }], companies: [{
      symbol: "NVDA", name: "NVIDIA Corporation", exchange: "NASDAQ", sector: "Technology", industry: "Semiconductors", price: "142.68", change: "+1.84%", change_tone: "up", series: [1, 2, 3], strength: 72, range: "1M", market_cap: "$3.4T", rating: "Positive", classification_label: "simulated classification",
    }], selected_sector: null, selected_industry: null, query: "", disclosure: "Synthetic fixtures only.", };
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const payload = url.includes("/discovery")
        ? { data: discovery, status: "ok", source: "synthetic-fixtures", freshness: "simulated", warnings: [] }
        : { data: { markets: [], sector_activity: [], disclosure: "Synthetic only." }, status: "ok", source: "synthetic-fixtures", freshness: "simulated", warnings: [] };
      return Promise.resolve(new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    await user.click(screen.getByRole("button", { name: "Discovery" }));
    expect(await screen.findByRole("table", { name: "Simulated company directory" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Show sample details for NVDA, NVIDIA Corporation/ })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/discovery"), expect.any(Object));
  });

  it("uses Python ticker search and renders raw FastAPI chart closes after range changes", async () => {
    const closes = [142.1, 143.25, 144.72];
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const data = url.includes("/tickers/search")
        ? { query: "AAPL", results: [{ symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", sector: "Technology", industry: "Consumer Electronics" }] }
        : url.includes("/chart")
          ? { symbol: new URL(url).pathname.match(/\/tickers\/([^/]+)\/chart/)?.[1] ?? "NVDA", range: new URL(url).searchParams.get("range"), interval: "1d", bars: closes.map((close, index) => ({ time: `2025-12-${28 + index}`, open: close - 1, high: close + 1, low: close - 2, close, volume: 1000 + index })), label: "Synthetic daily bars" }
          : url.includes("/analysis")
            ? { symbol: "NVDA", name: "NVIDIA Corporation", indicators: { last: 144.72, rsi: 54 }, move_source: "synthetic", trend_state: "Mixed sample trend", rating: "Hold", rating_source: "Python analytics.analyze", technical_rating: "Hold", analyst_rating: null, analyst_count: 0, analyst_score: null, analyst_period: null, constructive_checks: 2, caution_checks: 1, rating_checks_complete: true, rating_checks: [], returns: {}, observations: 320, hist_vol_observations: 319, drawdown_observations: 320, beta_observations: 300, as_of: "2025-12-31", disclosure: "Synthetic input." }
            : { markets: [{ name: "Synthetic index", symbol: "SYN", value: "100.00", change: "+0.1%", tone: "up", series: [1, 2, 3] }], sector_activity: [], disclosure: "Synthetic overview." };
      return Promise.resolve(new Response(JSON.stringify({ data, status: "ok", source: "python-engine-snapshot", freshness: "simulated", missing_fields: [], warnings: [], provenance: "engine-snapshot" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    const search = screen.getByRole("textbox", { name: /search ticker or company/i });
    await user.type(search, "AAPL");
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/tickers/search?q=AAPL"))).toBe(true));
    await user.click(await screen.findByRole("option", { name: /AAPL/ }));
    expect(await screen.findByRole("heading", { name: "Apple Inc." })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "1Y" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/chart?range=1Y"))).toBe(true));
    expect(await screen.findByText("144.72", { selector: ".legend-value" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "AAPL 1Y Python synthetic chart, area style" })).toBeInTheDocument();
  });

  it("renders normalized Python fundamentals, analyst data, neutral news, and technical checks", async () => {
    const research = { symbol: "NVDA", name: "NVIDIA Corporation", exchange: "NASDAQ", sector: "Technology", industry: "Semiconductors", fundamentals: [{ label: "Revenue · TTM", display_value: "$120.0B", raw_value: 120000000000, context: "Synthetic provider-shaped input" }], quarterly_financials: [{ period: "2025 Q4", revenue: 32000000000, operating_income: 12000000000, net_income: 10000000000, diluted_eps: 1.2 }], analyst_targets: { current: 144.72, high: 180, low: 120, mean: 155, median: 154, upside_percent: 7.1 }, analyst_consensus: { rating: "Buy", count: 8, score: 0.75, period: "current" }, recommendation_distribution: [{ rating: "Buy", count: 6 }, { rating: "Hold", count: 2 }], eps_revisions: [{ period: "Current quarter", up_last_7days: 2, up_last_30days: 4, down_last_7_days: 0, down_last_30days: 1 }], events: [{ date_label: "Synthetic date", title: "Illustrative earnings call", detail: "Synthetic event fixture." }], disclosure: "Synthetic inputs only.", as_of: "2025-12-31" };
    const news = { symbol: "NVDA", headlines: [{ title: "Synthetic neutral company update", publisher: "Fixture Wire", published_at: "2025-12-31", sentiment: "Neutral", confidence: "High", reason: "Balanced synthetic wording", issuer_relevant: true, bull_score: 0.2, bear_score: 0.2, topic: "Company update" }], events: [], disclosure: "Synthetic headline text only.", as_of: "2025-12-31" };
    const analysis = { symbol: "NVDA", name: "NVIDIA Corporation", indicators: { last: 144.72, sma20: 143, rsi: 54 }, move_source: "synthetic fixture", trend_state: "Mixed sample trend", rating: "Buy", rating_source: "existing analytics.analyze", technical_rating: "Buy", analyst_rating: "Buy", analyst_count: 8, analyst_score: 0.75, analyst_period: "current", constructive_checks: 3, caution_checks: 1, rating_checks_complete: true, rating_checks: [{ side: "Constructive", label: "Close above 20-day average", passed: true }], returns: { "3m": { excess: 0.04, observations: 60 } }, observations: 320, hist_vol_observations: 319, drawdown_observations: 320, beta_observations: 300, as_of: "2025-12-31", disclosure: "Synthetic data only." };
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      const data = url.includes("/news-events") ? news : url.endsWith("/analysis") ? analysis : url.includes("/research") ? research : { markets: [], sector_activity: [], disclosure: "Synthetic." };
      return Promise.resolve(new Response(JSON.stringify({ data, status: "ok", source: "python-engine-snapshot", freshness: "simulated", as_of: "2025-12-31", provenance: "engine-snapshot", missing_fields: [], warnings: [] }), { status: 200, headers: { "Content-Type": "application/json" } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    expect(await screen.findByText("$120.0B")).toBeInTheDocument();
    expect(screen.getByText("2025 Q4")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Analysts & events" }));
    expect(await screen.findByText("Buy", { selector: ".target-range strong" })).toBeInTheDocument();
    expect(screen.getByText("$155.00")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "News" }));
    expect((await screen.findAllByText("Synthetic neutral company update")).length).toBeGreaterThan(0);
    await user.selectOptions(screen.getByRole("combobox", { name: "Filter headline sentiment" }), "Neutral");
    expect(screen.getAllByText("Synthetic neutral company update").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("tab", { name: "Technical" }));
    expect(await screen.findByRole("heading", { name: "Buy · NVDA" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Rating calculation checks/ }));
    expect(screen.getByText(/Pass · Close above 20-day average/)).toBeInTheDocument();
  });

  it("surfaces a safe API failure in the active research tab", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ data: null, status: "failed", source: "python-engine-snapshot", freshness: "simulated", missing_fields: [], warnings: ["Synthetic research fixture is unavailable."] }), { status: 503, headers: { "Content-Type": "application/json" } })));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderDevelopmentApp();
    await user.selectOptions(screen.getByRole("combobox", { name: "Data mode" }), "fastapi");
    await user.click(screen.getByRole("button", { name: "Company Research" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Synthetic research fixture is unavailable.");
    expect(screen.getByRole("button", { name: "Retry local request" })).toBeInTheDocument();
  });

  it("opens the same preferences panel from sidebar and header and applies browser-local settings", async () => {
    const user = userEvent.setup();
    render(<App />);
    const preferenceButtons = screen.getAllByRole("button", { name: "Open Preferences" });
    await user.click(preferenceButtons[0]!);
    const dialog = screen.getByRole("dialog", { name: "Preferences" });
    await user.selectOptions(within(dialog).getByRole("combobox", { name: "Default TradingView symbol" }), "AAPL");
    await user.click(within(dialog).getByRole("checkbox", { name: "Reduce interface animations" }));
    await user.click(within(dialog).getByRole("checkbox", { name: "Collapse sidebar on desktop" }));
    await user.click(within(dialog).getByRole("button", { name: "Done" }));

    expect(document.querySelector(".sidebar")).toHaveClass("sidebar-collapsed");
    await waitFor(() => expect(JSON.parse(window.localStorage.getItem("jujosmi_trade_ui_preferences_v1") ?? "{}")).toMatchObject({ defaultSymbol: "AAPL", reduceAnimations: true, sidebarCollapsed: true }));
    await waitFor(() => expect(Array.from(document.querySelectorAll("script[src*='embed-widget-advanced-chart.js']")).some((script) => JSON.parse(script.textContent ?? "{}").symbol === "NASDAQ:AAPL")).toBe(true));

    await user.click(screen.getAllByRole("button", { name: "Open Preferences" })[1]!);
    expect(screen.getByRole("dialog", { name: "Preferences" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reset preferences" }));
    expect(within(screen.getByRole("dialog", { name: "Preferences" })).getByRole("combobox", { name: "Default TradingView symbol" })).toHaveValue("NVDA");
  });

  it("filters the searchable glossary and restores focus after Escape", async () => {
    const user = userEvent.setup();
    render(<App />);
    const helpButton = screen.getAllByRole("button", { name: "Open Help and glossary" })[0]!;
    await user.click(helpButton);
    const dialog = screen.getByRole("dialog", { name: "Help & glossary" });
    const search = within(dialog).getByRole("textbox", { name: "Search help and glossary" });
    expect(search).toHaveFocus();
    await user.type(search, "filing date");
    expect(within(dialog).getByText("Filing date vs. reporting period")).toBeInTheDocument();
    expect(within(dialog).queryByText("OHLCV")).not.toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Help & glossary" })).not.toBeInTheDocument());
    await waitFor(() => expect(helpButton).toHaveFocus());
  });

  it("routes Public Charts to Market Overview and preserves the chosen exchange-qualified symbol", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.selectOptions(screen.getByRole("combobox", { name: "Selected chart ticker" }), "JPM");
    await user.click(within(screen.getByRole("navigation", { name: "Workspaces" })).getByRole("button", { name: "Company Research" }));
    await user.click(screen.getByRole("button", { name: "Open Public Charts" }));
    expect(screen.getByRole("heading", { name: "Market Overview" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Data mode" })).toHaveValue("public");
    expect(screen.getByRole("heading", { name: "NYSE:JPM" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/market-overview");
    await waitFor(() => expect(JSON.parse(document.querySelector("script[src*='embed-widget-advanced-chart.js']")?.textContent ?? "{}").symbol).toBe("NYSE:JPM"));
  });

  it("makes Ctrl+K reach ticker search from another workspace", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(within(screen.getByRole("navigation", { name: "Workspaces" })).getByRole("button", { name: "Company Research" }));
    await user.keyboard("{Control>}k{/Control}");
    expect(await screen.findByRole("heading", { name: "Market Overview" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Find supported chart ticker" })).toHaveFocus();
  });

  it("does not expose a notifications control without a notification service", () => {
    render(<App />);
    expect(screen.queryByRole("button", { name: /notifications/i })).not.toBeInTheDocument();
  });
});
