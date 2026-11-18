import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ArrowDownRight, BarChart3, Bookmark, CalendarDays, ChevronDown, CircleHelp, Clock3, FileText, Filter, Search, ShieldCheck, TrendingUp } from "lucide-react";
import { SpotlightCard } from "./SpotlightCard";
import { WorkspaceTabs } from "./WorkspaceTabs";
import { ExpandableResearchCard } from "./ExpandableResearchCard";
import { fixtureRepository, sectors, type DirectoryFixture } from "../data/workspaceFixtures";
import { ApiRequestError, fetchCompanyResearch, fetchDiscovery, fetchDiscoveryCalendar, fetchNewsEvents, fetchSecDirectory, fetchSecFilings, fetchSecResearch, fetchTechnicalAnalysis, fetchWatchlistSummaries, type ApiEnvelope, type DiscoveryCalendarData, type DiscoveryData, type NewsEventsData, type ResearchData, type SecCompanyReport, type SecDirectoryData, type SecFilingsData, type TechnicalAnalysisData, type WatchlistSummaryData } from "../data/apiClient";
import type { DataMode } from "../types";
import { tradingViewTickerSymbols } from "../data/tradingViewSymbols";

type CommonProps = { selectedSymbol: string; selectedSecExchange?: string | null; selectedTicker: (typeof tickerFixtures)[number]; watchlist: string[]; onSelectTicker: (symbol: string, exchange?: string) => void; onNavigate: (workspace: "research" | "overview") => void };
const tickerFixtures = fixtureRepository.getTickers();
const companyResearchFixtures = fixtureRepository.getResearch();
const tickerFor = (symbol: string) => tickerFixtures.find((item) => item.symbol === symbol) ?? tickerFixtures[0]!;

function WorkspaceHeading({ kicker, title, description, badge = "SIMULATED FIXTURES" }: { kicker: string; title: string; description: string; badge?: string }) {
  return <header className="feature-heading"><div className="eyebrow"><span className="eyebrow-line" /> {kicker} <span className="sample-tag">{badge}</span></div><h1>{title}</h1><p>{description}</p></header>;
}

function FixtureBanner({ children = "All figures and classifications are illustrative UI fixtures, not live or verified research." }: { children?: string }) {
  return <div className="workspace-fixture-note"><ShieldCheck size={15} /><span>{children}</span></div>;
}

function DemoStateControls({ state, onChange }: { state: "ready" | "loading" | "error"; onChange: (state: "ready" | "loading" | "error") => void }) {
  return <div className="demo-state-controls" aria-label="Preview response states">{(["ready", "loading", "error"] as const).map((item) => <button key={item} className={state === item ? "selected" : ""} onClick={() => onChange(item)} aria-pressed={state === item}>{item === "ready" ? "Ready" : item === "loading" ? "Loading" : "Error"}</button>)}</div>;
}

function FixtureDiscoveryWorkspace({ selectedSymbol, onSelectTicker, onNavigate, dataMode = "fixtures" }: CommonProps & { dataMode?: Exclude<DataMode, "public"> }) {
  const [sector, setSector] = useState<(typeof sectors)[number]>("All sectors");
  const [industry, setIndustry] = useState("All industries");
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"directory" | "earnings" | "ipos">("directory");
  const [state, setState] = useState<"ready" | "loading" | "error">("ready");
  const [apiState, setApiState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [apiEnvelope, setApiEnvelope] = useState<ApiEnvelope<DiscoveryData> | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  useEffect(() => {
    if (dataMode !== "fastapi" || tab !== "directory") { setApiState("idle"); return; }
    const controller = new AbortController();
    setApiState("loading");
    setApiError(null);
    fetchDiscovery({ sector, industry, query }, controller.signal).then((response) => {
      setApiEnvelope(response);
      setApiState("ready");
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) { setApiEnvelope(null); setApiError(error instanceof ApiRequestError ? error.message : "The local API demo could not complete the request."); setApiState("error"); }
    });
    return () => controller.abort();
  }, [dataMode, tab, sector, industry, query, retryCount]);
  const industries = dataMode === "fastapi" && apiEnvelope?.data
    ? ["All industries", ...apiEnvelope.data.industries.filter((item) => sector === "All sectors" || item.sector === sector).map((item) => item.name)]
    : fixtureRepository.getIndustries(sector);
  const rows = useMemo(() => {
    if (dataMode === "fastapi") return (apiEnvelope?.data?.companies ?? []).map((item): DirectoryFixture => ({
      symbol: item.symbol, name: item.name, exchange: item.exchange, sector: item.sector, industry: item.industry,
      price: item.price, change: item.change, changeTone: item.change_tone, series: item.series, strength: item.strength,
      range: item.range, marketCap: item.market_cap, rating: item.rating,
    }));
    return fixtureRepository.getDirectory().filter((item) => (sector === "All sectors" || item.sector === sector) && (industry === "All industries" || item.industry === industry) && `${item.symbol} ${item.name} ${item.industry}`.toLowerCase().includes(query.toLowerCase()));
  }, [dataMode, apiEnvelope, sector, industry, query]);
  const showingLoading = dataMode === "fastapi" ? apiState === "loading" : state === "loading";
  const showingError = dataMode === "fastapi" ? apiState === "error" : state === "error";
  function changeSector(value: (typeof sectors)[number]) { setSector(value); setIndustry("All industries"); }
  return <div className="functional-workspace">
    <WorkspaceHeading kicker="DISCOVERY WORKSPACE" title="Explore the market." description="Filter a sample company directory by sector and industry, or scan upcoming event fixtures." />
    <FixtureBanner>{dataMode === "fastapi" ? "Discovery results are deterministic synthetic API fixtures. Company classifications and metrics are simulated, not verified." : "Company classifications, event dates, and values below are simulated fixtures for interface evaluation."}</FixtureBanner>
    <div className="discovery-toolbar"><label className="directory-search"><Search size={16} /><input aria-label="Search companies or industries" placeholder="Search companies, tickers, industries…" value={query} onChange={(event) => setQuery(event.target.value)} /><kbd>Filter listings</kbd></label><label className="filter-select"><Filter size={14} /><span>Sector</span><select aria-label="Filter sector" value={sector} onChange={(event) => changeSector(event.target.value as (typeof sectors)[number])}>{sectors.map((item) => <option key={item}>{item}</option>)}</select><ChevronDown size={13} /></label><label className="filter-select"><span>Industry</span><select aria-label="Filter industry" value={industries.includes(industry) ? industry : "All industries"} onChange={(event) => setIndustry(event.target.value)}>{industries.map((item) => <option key={item}>{item}</option>)}</select><ChevronDown size={13} /></label></div>
    <WorkspaceTabs label="Discovery views" items={["Industry directory", "Earnings soon", "IPO calendar"]} value={tab === "directory" ? "Industry directory" : tab === "earnings" ? "Earnings soon" : "IPO calendar"} onChange={(value) => setTab(value === "Industry directory" ? "directory" : value === "Earnings soon" ? "earnings" : "ipos")} />
    <div className="discovery-summary-row"><div><span className="section-kicker">{tab === "directory" ? "COMPANY DIRECTORY" : tab === "earnings" ? "UPCOMING EARNINGS · SAMPLE" : "NEW LISTINGS · SAMPLE"}</span><h2>{tab === "directory" ? `${rows.length} companies in view` : tab === "earnings" ? "Upcoming earnings fixtures" : "IPO calendar fixtures"}</h2></div>{dataMode === "fixtures" && <DemoStateControls state={state} onChange={setState} />}</div>
    {showingLoading ? <div className="workspace-state" role="status"><span className="loading-ring" /> {dataMode === "fastapi" ? "Requesting synthetic directory from local API…" : "Loading illustrative directory…"}</div> : showingError ? <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18} /><div><b>{dataMode === "fastapi" ? "Local API request failed" : "Sample directory unavailable"}</b><span>{dataMode === "fastapi" ? apiError ?? "Confirm the Python demonstration API is running at localhost:8000." : "This is a local error-state preview. No provider request was made."}</span></div>{dataMode === "fastapi" ? <button className="quiet-button" onClick={() => setRetryCount((value) => value + 1)}>Retry API request</button> : <button className="quiet-button" onClick={() => setState("ready")}>Try fixture again</button>}</div> : tab === "directory" ? <SpotlightCard className="data-table-card"><div className="directory-table" role="table" aria-label="Simulated company directory"><div className="directory-row directory-head" role="row"><span>COMPANY</span><span>SECTOR · INDUSTRY</span><span>FIXTURE SIGNAL</span><span>MARKET CAP</span></div>{rows.map((item) => <DirectoryRow key={item.symbol} item={item} selected={selectedSymbol === item.symbol} onSelect={() => onSelectTicker(item.symbol)} onResearch={() => { onSelectTicker(item.symbol); onNavigate("research"); }} />)}{!rows.length && <div className="table-empty">{dataMode === "fastapi" ? apiEnvelope?.warnings[0] ?? "No synthetic company fixtures match these filters." : "No simulated company matches. Adjust the search or filters."}</div>}</div><div className="table-footnote"><span>{rows.length} simulated listings</span><span>Directory classifications are examples, not verified company data.</span></div></SpotlightCard> : dataMode === "fastapi" ? <DiscoveryCalendarView kind={tab} onSelectTicker={onSelectTicker} onNavigate={onNavigate} /> : <div className="event-list">{(tab === "earnings" ? companyResearchFixtures.events : [["Aug 14", "Example public listing", "Illustrative calendar fixture"], ["Sep 03", "Sample technology offering", "No live offering information"], ["Oct 11", "Example consumer company listing", "Illustrative date only"]] as const).map(([date, title, detail]) => <SpotlightCard className="event-row" key={title}><div className="event-date"><CalendarDays size={16} /><b>{date}</b></div><div><h3>{title}</h3><p>{detail}</p></div><span className="event-status">{tab === "earnings" ? "EARNINGS FIXTURE" : "IPO FIXTURE"}</span></SpotlightCard>)}</div>}
    {dataMode === "fastapi" && tab === "directory" && apiEnvelope?.stale && <p className="table-caption" role="status">This directory is the last successful response and is marked stale.</p>}
    <div className="workspace-help-note"><CircleHelp size={14} /><span>These controls demonstrate the Discovery workflow. No company classification has been independently verified.</span></div>
  </div>;
}

function DirectoryRow({ item, selected, onSelect, onResearch }: { item: DirectoryFixture; selected: boolean; onSelect: () => void; onResearch: () => void }) {
  return <div className={`directory-row ${selected ? "directory-row-selected" : ""}`} role="row"><ExpandableResearchCard title={`${item.symbol} · ${item.name}`} subtitle={`${item.exchange} · ${item.sector} · ${item.industry}`} preview={<><span className="directory-avatar">{item.symbol.slice(0, 1)}</span><span><b>{item.symbol}</b><small>{item.name}</small></span></>} className="directory-company directory-company-expand" label={`Show sample details for ${item.symbol}, ${item.name}`} onOpen={onSelect}><div className="expandable-fact-grid"><div><span>Sector</span><b>{item.sector}</b></div><div><span>Industry</span><b>{item.industry}</b></div><div><span>Sample strength</span><b>{item.strength} / 100</b></div><div><span>Sample rating label</span><b>{item.rating}</b></div><div><span>Illustrative price</span><b>${item.price}</b></div><div><span>Illustrative market cap</span><b>{item.marketCap}</b></div></div><p className="table-caption">Classification and financial values are simulated demonstration fixtures; no company directory source is connected.</p><button type="button" className="outline-button expandable-action" onClick={onResearch}>Open Company Research <ArrowDownRight size={14} /></button></ExpandableResearchCard><span className="directory-industry"><b>{item.sector}</b><small>{item.industry}</small></span><span><i className={`rating-chip rating-${item.rating.toLowerCase()}`}>{item.rating}</i></span><span className="directory-cap">{item.marketCap}<small>sample cap</small></span><button className="row-research" onClick={onResearch} aria-label={`Research ${item.symbol}`}>Research <ArrowDownRight size={13} /></button></div>;
}

function DiscoveryCalendarView({ kind, onSelectTicker, onNavigate }: { kind: "earnings" | "ipos"; onSelectTicker: (symbol: string) => void; onNavigate: (workspace: "research" | "overview") => void }) {
  const [response, setResponse] = useState<ApiEnvelope<DiscoveryCalendarData> | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setResponse(null); setError("");
    fetchDiscoveryCalendar(kind, 60, controller.signal).then(setResponse).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof ApiRequestError ? cause.message : "The local calendar API could not complete the request.");
    });
    return () => controller.abort();
  }, [kind, retry]);
  if (error) return <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18} /><div><b>Calendar response unavailable</b><span>{error}</span></div><button className="quiet-button" onClick={() => setRetry((value) => value + 1)}>Retry local request</button></div>;
  if (!response?.data) return <div className="workspace-state" role="status"><span className="loading-ring" /> Requesting synthetic calendar fixtures from local API…</div>;
  const items = response.data.items;
  return <><div className="event-list">{items.map((item) => <SpotlightCard className="event-row" key={`${item.symbol}-${item.title}`}><div className="event-date"><CalendarDays size={16} /><b>{item.date_label}</b></div><div><h3>{item.title}</h3><p>{item.name} · {item.detail}</p></div><span className="event-status">{kind === "earnings" ? "EARNINGS FIXTURE" : "IPO FIXTURE"}</span>{tickerFixtures.some((ticker) => ticker.symbol === item.symbol) && <button className="icon-button" aria-label={`Research ${item.symbol}`} onClick={() => { onSelectTicker(item.symbol); onNavigate("research"); }}><ArrowDownRight size={16} /></button>}</SpotlightCard>)}{!items.length && <div className="table-empty">No synthetic calendar items were returned for this request.</div>}</div><p className="table-caption">{response.data.disclosure}</p>{response.warnings.length > 0 && <p className="table-caption" role="status">{response.warnings.join(" ")}</p>}</>;
}

function FixtureResearchWorkspace({ selectedTicker, onNavigate }: CommonProps) {
  const [tab, setTab] = useState("Overview");
  const [state, setState] = useState<"ready" | "loading" | "error">("ready");
  const ticker = selectedTicker;
  const tabs = ["Overview", "Financials", "Analysts & events", "News", "Technical"];
  return <div className="functional-workspace">
    <WorkspaceHeading kicker="COMPANY RESEARCH" title="One company. A fuller picture." description="A structured view of business performance, expectations, events, and price context." />
    <FixtureBanner>All fundamentals, analyst views, dates, and headlines are illustrative fixtures. They are not current or investment advice.</FixtureBanner>
    <div className="research-company-header"><div className="ticker-avatar">{ticker.symbol.slice(0, 1)}</div><div className="research-company-name"><span>{ticker.exchange} · {ticker.sector} · {ticker.industry}</span><h2>{ticker.name} <small>{ticker.symbol}</small></h2><p><span className="fixture-indicator-dot" /> Sample company profile · not connected to a provider</p></div><button className="outline-button" onClick={() => onNavigate("overview")}>Market overview <ArrowDownRight size={14} /></button></div>
    <WorkspaceTabs label="Company research sections" items={tabs} value={tab} onChange={setTab} />
    <div className="discovery-summary-row"><div><span className="section-kicker">{tab.toUpperCase()} · {ticker.symbol}</span><h2>{tab === "Overview" ? "Business & valuation" : tab}</h2></div><DemoStateControls state={state} onChange={setState} /></div>
    {state === "loading" ? <div className="workspace-state" role="status"><span className="loading-ring" /> Loading illustrative company research…</div> : state === "error" ? <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18} /><div><b>Sample research unavailable</b><span>This is a local error-state preview. No provider request was made.</span></div><button className="quiet-button" onClick={() => setState("ready")}>Try fixture again</button></div> : <ResearchPanel tab={tab} ticker={ticker} />}
  </div>;
}

export function ResearchWorkspace(props: CommonProps & { dataMode?: DataMode }) {
  if (props.dataMode === "public") return <PublicResearchWorkspace symbol={props.selectedSymbol} exchange={props.selectedSecExchange} onNavigate={props.onNavigate} />;
  return props.dataMode === "fastapi" ? <EngineResearchWorkspace {...props} /> : <FixtureResearchWorkspace {...props} />;
}

function PublicResearchWorkspace({ symbol, exchange, onNavigate }: { symbol: string; exchange?: string | null; onNavigate: (workspace: "research" | "overview") => void }) {
  const [tab, setTab] = useState("Overview");
  const [secResponse, setSecResponse] = useState<ApiEnvelope<SecCompanyReport> | null>(null);
  const [secError, setSecError] = useState("");
  const [secLoading, setSecLoading] = useState(false);
  const tabs = ["Overview", "Financials", "Analysts & events", "News", "Technical"];
  const names: Record<string, string> = { Overview: "Business & valuation", Financials: "Reported financials", "Analysts & events": "Analyst & company events", News: "Headlines & sentiment", Technical: "Technical & relative strength" };
  useEffect(() => {
    if (tab !== "Overview" && tab !== "Financials") return;
    const controller = new AbortController();
    setSecLoading(true); setSecError(""); setSecResponse(null);
    fetchSecResearch(symbol, controller.signal, exchange).then(setSecResponse).catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setSecError(error instanceof ApiRequestError ? error.message : "SEC reported company information is unavailable.");
    }).finally(() => { if (!controller.signal.aborted) setSecLoading(false); });
    return () => controller.abort();
  }, [symbol, exchange, tab]);
  const secReport = secResponse?.data ?? undefined;
  return <div className="functional-workspace">
    <WorkspaceHeading kicker="COMPANY RESEARCH" title="Research with clear sources." description="Public research panels are shown only when their sources and usage terms are established." badge="PUBLIC SOURCE STATUS" />
    <div className="research-company-header"><div className="ticker-avatar">{(secReport?.identity.name ?? symbol).slice(0, 1)}</div><div className="research-company-name"><span>{secReport ? `CIK ${secReport.identity.cik} · ${secReport.identity.exchange ?? "Exchange not listed"} · SEC issuer identity` : "SEC issuer identity"}</span><h2>{secReport?.identity.name ?? symbol} <small>{secReport?.identity.ticker ?? symbol}</small></h2><p><span className="fixture-indicator-dot" />{secReport ? "Company identity verified against SEC ticker/CIK directory" : "Identity loads from the official SEC directory when available"}</p></div><button className="outline-button" onClick={() => onNavigate("overview")}>Market overview <ArrowDownRight size={14} /></button></div>
    <WorkspaceTabs label="Company research sections" items={tabs} value={tab} onChange={setTab} />
    <div className="discovery-summary-row"><div><span className="section-kicker">{tab.toUpperCase()} · {symbol}</span><h2>{names[tab]}</h2></div></div>
    {tab === "Overview" || tab === "Financials" ? <SecFinancialPanel loading={secLoading} error={secError} report={secReport} envelope={secResponse} mode={tab} /> : <UnavailablePanel title={names[tab]} detail="This feature is retained in the application, but no source with verified public-use rights is connected. No synthetic or personal-use data is substituted in public mode. TradingView's chart remains a separate embed and is not used to calculate these research panels." />}
  </div>;
}

function SecFinancialPanel({ loading, error, report, envelope, mode }: { loading: boolean; error: string; report?: SecCompanyReport; envelope: ApiEnvelope<SecCompanyReport> | null; mode: "Overview" | "Financials" }) {
  if (loading) return <div className="workspace-state" role="status"><span className="loading-ring" /> Loading reported SEC filings and financial facts…</div>;
  if (error) return <section className="public-unavailable-card" role="alert"><span className="section-kicker">SEC DATA UNAVAILABLE</span><h3>Reported company information could not be loaded</h3><p>{error}</p><p>Check the local Python API and its identifying SEC User-Agent configuration. No financial values have been substituted.</p></section>;
  if (!report) return <UnavailablePanel title="SEC company facts unavailable" detail="No response was returned. No financial values have been substituted." />;
  const factLabels: Record<string, string> = { revenue: "Revenue", net_income: "Net income", operating_income: "Operating income", diluted_eps: "Diluted EPS", assets: "Assets", liabilities: "Liabilities", cash_and_equivalents: "Cash and cash equivalents" };
  const recentFilings = report.filings.filter((filing) => ["10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A"].includes(filing.form)).slice(0, 12);
  const factsByField = new Map<string, SecCompanyReport["facts"]>();
  report.facts.forEach((fact) => factsByField.set(fact.field, [...(factsByField.get(fact.field) ?? []), fact]));
  return <div className="sec-research-content">
    <section className="public-unavailable-card sec-source-card"><div className="sec-title-row"><div><span className="section-kicker">{envelope?.status === "partial" || report.status === "partial" ? "PARTIAL SEC REPORT" : "SEC REPORTED DATA"}</span><h3>{mode === "Overview" ? "Company facts & latest filings" : "Reported financial facts"}</h3></div><span className="sec-freshness">{envelope?.freshness === "cached" ? "CACHED" : "LIVE SEC"}</span></div><p>Source: U.S. Securities and Exchange Commission EDGAR · Retrieved {report.as_of ? new Date(report.as_of).toLocaleString() : "time unavailable"} · values are reported as filed, without derived ratios or TTM estimates.</p>{report.warnings.map((warning) => <p className="sec-warning" role="status" key={warning}>{warning}</p>)}</section>
    {mode === "Overview" ? <>
      <div className="sec-fact-grid">{["revenue", "net_income", "operating_income", "diluted_eps", "assets", "liabilities", "cash_and_equivalents"].map((field) => { const versions = factsByField.get(field) ?? []; const latest = [...versions].filter((fact) => fact.latest_reported_version).sort((a, b) => b.period_end.localeCompare(a.period_end))[0]; return <article className="sec-fact-card" key={field}><span>{factLabels[field]}</span><b>{latest ? `${latest.original_value} ${latest.unit}` : "Not reported / unavailable"}</b><small>{latest ? `${latest.form} · ${latest.period_start ? `${latest.period_start} to ` : "As of "}${latest.period_end} · filed ${latest.filed}` : "No mapped standard SEC fact"}</small>{latest && <small>Taxonomy: {latest.taxonomy} · {latest.tag}</small>}</article>; })}</div>
      <SecFilings filings={recentFilings} />
    </> : <>
      <div className="sec-table-scroll" role="region" aria-label="SEC reported financial facts" tabIndex={0}><table className="sec-facts-table"><thead><tr><th scope="col">Reported concept</th><th scope="col">Original value</th><th scope="col">Unit</th><th scope="col">Period</th><th scope="col">Filed</th><th scope="col">Filing</th><th scope="col">Version</th></tr></thead><tbody>{report.facts.map((fact, index) => <tr key={`${fact.field}-${fact.unit}-${fact.period_end}-${fact.accession_number}-${index}`}><th scope="row">{factLabels[fact.field] ?? fact.label}<small>{fact.taxonomy} · {fact.tag}</small></th><td>{fact.original_value}</td><td>{fact.unit}</td><td>{fact.period_start ? `${fact.period_start} – ` : ""}{fact.period_end} · {fact.fiscal_period ?? fact.form}</td><td>{fact.filed}</td><td>{fact.filing_url ? <a href={fact.filing_url} target="_blank" rel="noreferrer">{fact.accession_number}</a> : fact.accession_number}</td><td>{fact.latest_reported_version ? "Latest reported version" : "Earlier reported version"}</td></tr>)}</tbody></table>{report.facts.length === 0 && <p className="table-empty">No mapped standard facts were returned. The SEC does not include company-specific extensions in Company Facts.</p>}</div>
      <SecFilings filings={recentFilings} />
      {report.missing_fields.length > 0 && <p className="table-caption">Not present in the mapped standard taxonomy: {report.missing_fields.map((field) => factLabels[field] ?? field).join(", ")}.</p>}
    </>}
    <p className="table-caption">Each value retains the SEC taxonomy, unit, fiscal/report period, filed date, accession number, and filing link where provided. Filing revisions are retained as separate records.</p>
  </div>;
}

function SecFilings({ filings }: { filings: SecCompanyReport["filings"] }) {
  return <section className="sec-filings"><span className="section-kicker">SEC SUBMISSIONS HISTORY</span><h3>Recent annual and quarterly filings</h3>{filings.length ? <ul>{filings.map((filing) => <li key={filing.accession_number}><div><b>{filing.form}</b><span>Filed {filing.filing_date} · report period {filing.report_period ?? "not provided"}</span><small>Accession {filing.accession_number}</small></div>{filing.filing_url && <a href={filing.filing_url} target="_blank" rel="noreferrer">Open filing <FileText size={14} /></a>}</li>)}</ul> : <p>No recent 10-K, 10-Q, 20-F, or 40-F filings were available in the SEC submissions response.</p>}</section>;
}

function UnavailablePanel({ title, detail }: { title: string; detail: string }) {
  return <section className="public-unavailable-card"><span className="section-kicker">UNAVAILABLE · NO SOURCE CONNECTED</span><h3>{title}</h3><p>{detail}</p></section>;
}

export function DiscoveryWorkspace(props: CommonProps & { dataMode?: DataMode }) {
  if (props.dataMode === "public") return <PublicDiscoveryWorkspace selectedSymbol={props.selectedSymbol} onSelectTicker={props.onSelectTicker} onNavigate={props.onNavigate} />;
  return <FixtureDiscoveryWorkspace {...props} dataMode={props.dataMode ?? "fixtures"} />;
}

function PublicDiscoveryWorkspace({ selectedSymbol, onSelectTicker, onNavigate }: Pick<CommonProps, "selectedSymbol" | "onSelectTicker" | "onNavigate">) {
  const pageSize = 25;
  const [tab, setTab] = useState("Company directory");
  const [query, setQuery] = useState("");
  const [exchange, setExchange] = useState("");
  const [page, setPage] = useState(0);
  const [directory, setDirectory] = useState<ApiEnvelope<SecDirectoryData> | null>(null);
  const [directoryState, setDirectoryState] = useState<"loading" | "ready" | "error">("loading");
  const [directoryError, setDirectoryError] = useState("");
  const [directoryRetry, setDirectoryRetry] = useState(0);
  const [filingSymbol, setFilingSymbol] = useState("");
  const [filingExchange, setFilingExchange] = useState("");
  const [submittedFiling, setSubmittedFiling] = useState<{symbol:string;exchange:string;retry:number}|null>(null);
  const [filings, setFilings] = useState<ApiEnvelope<SecFilingsData> | null>(null);
  const [filingsState, setFilingsState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [filingsError, setFilingsError] = useState("");
  useEffect(() => {
    if (tab !== "Company directory") return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setDirectoryState("loading"); setDirectoryError("");
      fetchSecDirectory({query:query.trim(),exchange,limit:pageSize,offset:page*pageSize},controller.signal).then((response) => {
        setDirectory(response); setDirectoryState("ready");
      }).catch((cause:unknown) => {
        if (!controller.signal.aborted) { setDirectory(null); setDirectoryError(cause instanceof ApiRequestError ? cause.message : "The SEC company directory could not be loaded."); setDirectoryState("error"); }
      });
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [tab, query, exchange, page, directoryRetry]);
  useEffect(() => {
    if (!submittedFiling || tab !== "Recent SEC filings") return;
    const controller = new AbortController();
    setFilingsState("loading"); setFilingsError(""); setFilings(null);
    fetchSecFilings(submittedFiling.symbol,submittedFiling.exchange || undefined,controller.signal).then((response) => {
      setFilings(response); setFilingsState("ready");
    }).catch((cause:unknown) => {
      if (!controller.signal.aborted) { setFilingsError(cause instanceof ApiRequestError ? cause.message : "SEC filing history could not be loaded."); setFilingsState("error"); }
    });
    return () => controller.abort();
  }, [tab, submittedFiling]);
  const exchangeOptions = directory?.data?.available_exchanges ?? [];
  const items = directory?.data?.companies ?? [];
  function showCompanyFilings(symbol:string, selectedExchange:string|null) {
    const nextExchange=selectedExchange ?? "";
    setFilingSymbol(symbol); setFilingExchange(nextExchange); setSubmittedFiling({symbol,exchange:nextExchange,retry:Date.now()}); setTab("Recent SEC filings");
  }
  function loadFilings(event:FormEvent<HTMLFormElement>) {
    event.preventDefault(); const symbol=filingSymbol.trim().toUpperCase();
    if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol)) { setFilings(null);setFilingsError("Enter a ticker symbol, or select a company from the SEC directory.");setFilingsState("error");return; }
    setSubmittedFiling({symbol,exchange:filingExchange.trim(),retry:Date.now()});
  }
  return <div className="functional-workspace">
    <WorkspaceHeading kicker="DISCOVERY WORKSPACE" title="Explore SEC company records." description="Search public company identity records and inspect actual filing history from official EDGAR data." badge="SEC EDGAR · PUBLIC RECORDS" />
    <div className="public-data-note"><ShieldCheck size={16} /><span>The SEC ticker directory is an association file, not a complete or authoritative list of currently tradable securities. It does not provide GICS sector or industry classifications. Filing dates are actual submissions, not scheduled earnings events.</span></div>
    <WorkspaceTabs label="Discovery views" items={["Company directory", "Recent SEC filings", "Earnings soon", "IPO calendar"]} value={tab} onChange={setTab} />
    {tab === "Company directory" ? <>
      <div className="discovery-toolbar sec-directory-toolbar"><label className="directory-search"><Search size={16} /><input aria-label="Search SEC companies by name or ticker" placeholder="Search company name or ticker…" maxLength={60} value={query} onChange={(event) => { setQuery(event.target.value);setPage(0); }} /><kbd>SEC records</kbd></label><label className="filter-select"><Filter size={14} /><span>Exchange</span><select aria-label="Filter by exchange" value={exchange} onChange={(event) => {setExchange(event.target.value);setPage(0);}}><option value="">All exchanges</option>{exchangeOptions.map((item)=><option key={item} value={item}>{item}</option>)}</select><ChevronDown size={13} /></label></div>
      <div className="discovery-summary-row"><div><span className="section-kicker">SEC COMPANY TICKER DIRECTORY</span><h2>{directoryState === "ready" ? `${directory?.data?.total.toLocaleString() ?? 0} matching SEC records` : "Search company identity records"}</h2></div>{directory && <span className="sec-freshness">{directory.freshness === "cached" ? "SEC DIRECTORY · CACHED" : "SEC DIRECTORY · RETRIEVED"}</span>}</div>
      <p className="sec-discovery-source">Official source: <a href="https://www.sec.gov/files/company_tickers_exchange.json" target="_blank" rel="noreferrer">SEC company_tickers_exchange.json</a>{directory?.as_of ? ` · Retrieved ${new Date(directory.as_of).toLocaleString()}` : ""}</p>
      {directoryState === "loading" ? <div className="workspace-state" role="status"><span className="loading-ring" /> Requesting the SEC company directory…</div> : directoryState === "error" ? <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18} /><div><b>SEC directory unavailable</b><span>{directoryError}</span></div><button className="quiet-button" onClick={() => setDirectoryRetry((value)=>value+1)}>Retry directory request</button></div> : <>
        <div className="sec-directory-table" role="table" aria-label="SEC company ticker and exchange records"><div className="sec-directory-row sec-directory-head" role="row"><span>COMPANY · TICKER</span><span>EXCHANGE</span><span>SEC CIK</span><span>RESEARCH</span></div>
          {items.map((item)=><div className={`sec-directory-row ${selectedSymbol===item.ticker ? "sec-directory-row-selected" : ""}`} role="row" key={`${item.cik}-${item.ticker}-${item.exchange ?? ""}`}><button className="sec-company-select" aria-pressed={selectedSymbol===item.ticker} onClick={()=>onSelectTicker(item.ticker,item.exchange ?? undefined)} aria-label={`Select ${item.name} (${item.ticker})`}><span className="directory-avatar">{item.ticker.slice(0,1)}</span><span><b>{item.name}</b><small>{item.ticker}</small></span></button><span>{item.exchange ?? "Not supplied"}</span><code>{item.cik}</code><div className="sec-company-actions"><button className="row-research" aria-label={`Open Company Research for ${item.name} (${item.ticker})`} onClick={()=>{onSelectTicker(item.ticker,item.exchange ?? undefined);onNavigate("research");}}>Company Research <ArrowDownRight size={13}/></button><button className="quiet-button" onClick={()=>showCompanyFilings(item.ticker,item.exchange)}>Recent filings</button></div></div>)}
          {!items.length && <div className="table-empty">No SEC directory records matched this search. Try a ticker or a broader company name.</div>}
        </div>
        <div className="sec-pagination"><span>Showing {items.length ? directory!.data!.offset+1 : 0}–{directory!.data!.offset+items.length} of {directory!.data!.total.toLocaleString()}</span><div><button className="quiet-button" disabled={page===0} onClick={()=>setPage((value)=>Math.max(0,value-1))}>Previous</button><button className="quiet-button" disabled={directory!.data!.offset+items.length>=directory!.data!.total} onClick={()=>setPage((value)=>value+1)}>Next</button></div></div>
      </>}
      {directory?.stale && <p className="table-caption" role="status">Showing a previously successful SEC directory response; the latest request is marked stale.</p>}
    </> : tab === "Recent SEC filings" ? <>
      <div className="discovery-summary-row"><div><span className="section-kicker">ISSUER SUBMISSIONS</span><h2>Recent filings by company</h2></div></div>
      <p className="sec-discovery-source">Select “Recent filings” on a directory result, or enter an exact SEC ticker. The exchange selector on directory results disambiguates duplicate ticker symbols.</p>
      <form className="sec-filings-search" onSubmit={loadFilings}><label>Company ticker<input aria-label="Company ticker for filing search" value={filingSymbol} onChange={(event)=>setFilingSymbol(event.target.value.toUpperCase())} maxLength={10} placeholder="e.g. AAPL" /></label><label>Exchange (optional)<input aria-label="Exchange for filing search" value={filingExchange} onChange={(event)=>setFilingExchange(event.target.value)} maxLength={40} placeholder="Select from directory if needed" /></label><button className="primary-button" type="submit">Load SEC filings</button></form>
      {filingsError && filingsState === "error" && <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18}/><div><b>Filing history unavailable</b><span>{filingsError}</span></div>{submittedFiling && <button className="quiet-button" onClick={()=>setSubmittedFiling({...submittedFiling,retry:Date.now()})}>Retry</button>}</div>}
      {filingsState === "loading" && <div className="workspace-state" role="status"><span className="loading-ring"/> Requesting this issuer’s SEC submissions…</div>}
      {filings && filings.data && <><div className="sec-issuer-summary"><div><span className="section-kicker">{filings.freshness === "cached" ? "CACHED SEC SUBMISSIONS" : "SEC SUBMISSIONS"}</span><h3>{filings.data.company_name} <small>{filings.data.ticker}</small></h3><p>CIK {filings.data.cik}{filings.data.exchange ? ` · ${filings.data.exchange}` : ""}{filings.data.sic_description ? ` · SIC ${filings.data.sic ?? ""}: ${filings.data.sic_description}` : " · SEC SIC classification unavailable"}</p></div><span className="sec-freshness">{filings.freshness.toUpperCase()}</span></div><p className="sec-discovery-source">Retrieved {filings.as_of ? new Date(filings.as_of).toLocaleString() : "timestamp unavailable"} · <a href={`https://www.sec.gov/edgar/browse/?CIK=${filings.data.cik}&owner=exclude`} target="_blank" rel="noreferrer">SEC issuer filings</a></p>{filings.data.filings.length ? <div className="sec-filings-list">{filings.data.filings.map((filing)=><article className="sec-filing-row" key={filing.accession_number}><div><span className="rating-chip rating-balanced">{filing.form}</span><h3>{filing.company_name}</h3><p>Filed {filing.filing_date}{filing.report_date ? ` · reporting period ${filing.report_date}` : " · report period not supplied"}</p><small>Accession {filing.accession_number}</small></div>{filing.filing_url && <a className="row-research" href={filing.filing_url} target="_blank" rel="noreferrer">Open filing <ArrowDownRight size={13}/></a>}</article>)}</div> : <div className="table-empty">No recent 10-K, 10-Q, 8-K, or S-1 entries were returned for this issuer.</div>}{filings.warnings.map((warning)=><p className="table-caption" role="status" key={warning}>{warning}</p>)}<p className="table-caption">{filings.data.disclosure}</p></>}
    </> : <UnavailablePanel title={tab === "Earnings soon" ? "Scheduled earnings dates unavailable" : "IPO trading dates unavailable"} detail={tab === "Earnings soon" ? "SEC submissions show filed documents, not future earnings schedules. No approved scheduled-events source is connected." : "An S-1 registration statement is not a confirmed IPO date. SEC filings do not provide a reliable future IPO calendar here."} />}
  </div>;
}

function ResearchPanel({ tab, ticker }: { tab: string; ticker: ReturnType<typeof tickerFor> }) {
  if (tab === "Overview" || tab === "Financials") return <><div className="research-metric-grid">{companyResearchFixtures.fundamentals.map(([label, value, detail]) => <ExpandableResearchCard className="research-metric" key={label} title={label} subtitle={`${ticker.symbol} · simulated company research`} preview={<><span>{label}</span><strong>{value}</strong><small>{detail}</small></>}><div className="expandable-fact-grid"><div><span>Metric</span><b>{label}</b></div><div><span>Sample value</span><b>{value}</b></div><div><span>Context</span><b>{detail}</b></div></div><p className="table-caption">This value is an existing interface fixture. No statements, provider feed, or valuation model is connected.</p></ExpandableResearchCard>)}</div><div className="research-columns"><SpotlightCard className="research-panel"><div className="card-heading"><div><span className="section-kicker">BUSINESS SNAPSHOT</span><h3>Operating context</h3></div><BarChart3 size={16} /></div><p className="research-copy">Illustrative overview for {ticker.name}. This panel is a presentation fixture and does not contain verified company fundamentals.</p><div className="context-list"><div><span>Sector</span><b>{ticker.sector}</b></div><div><span>Industry</span><b>{ticker.industry}</b></div><div><span>Revenue growth</span><b>+12.6% <small>sample</small></b></div><div><span>Valuation context</span><b>31.8× forward P/E <small>sample</small></b></div></div></SpotlightCard><SpotlightCard className="research-panel"><div className="card-heading"><div><span className="section-kicker">QUARTERLY FINANCIALS</span><h3>Recent periods</h3></div><span className="sample-tag">ILLUSTRATIVE</span></div><div className="financial-table"><div><span>Period</span><span>Revenue</span><span>Operating income</span><span>Net income</span></div>{companyResearchFixtures.quarters.map(([period, revenue, operating, net]) => <div key={period}><b>{period}</b><span>{revenue}</span><span>{operating}</span><span>{net}</span></div>)}</div><p className="table-caption">Values shown are sample content only. No financial statement source is connected.</p></SpotlightCard></div></>;
  if (tab === "Analysts & events") return <div className="research-columns"><SpotlightCard className="research-panel analyst-panel"><div className="card-heading"><div><span className="section-kicker">ILLUSTRATIVE STREET CONSENSUS</span><h3>Analyst expectations</h3></div><TrendingUp size={16} /></div><div className="target-range"><span>Sample average target</span><strong>{companyResearchFixtures.target}</strong><small>Fixture range {companyResearchFixtures.lowTarget} – {companyResearchFixtures.highTarget}</small><ExpandableResearchCard title="Analyst expectation fixtures" subtitle={`${ticker.symbol} · simulated consensus`} preview={<span>Average target {companyResearchFixtures.target} · sample only</span>} className="analyst-detail-trigger"><div className="expandable-fact-grid"><div><span>Average target</span><b>{companyResearchFixtures.target}</b></div><div><span>Sample range</span><b>{companyResearchFixtures.lowTarget} – {companyResearchFixtures.highTarget}</b></div><div><span>Coverage</span><b>Illustrative only</b></div></div><p className="table-caption">No real analyst consensus or price target feed is connected.</p></ExpandableResearchCard></div><div className="rating-bars">{companyResearchFixtures.analysts.map(([label, value]) => <div key={label}><span>{label}</span><div><i className={`bar-${label.toLowerCase()}`} style={{ width: `${value}%` }} /></div><b>{value}%</b></div>)}</div><p className="table-caption">Illustrative consensus distribution; no analyst feed is connected.</p></SpotlightCard><SpotlightCard className="research-panel"><div className="card-heading"><div><span className="section-kicker">COMPANY CALENDAR</span><h3>Earnings & events</h3></div><CalendarDays size={16} /></div><div className="timeline">{companyResearchFixtures.events.map(([date, title, detail]) => <ExpandableResearchCard key={title} title={title} subtitle={`${date} · ${detail}`} preview={<span>Open illustrative event details</span>} className="event-detail-trigger"><p>This calendar entry is an existing UI fixture. Its date and event details have not been verified against a company filing or calendar source.</p></ExpandableResearchCard>)}</div></SpotlightCard><SpotlightCard className="research-panel wide-panel"><div className="card-heading"><div><span className="section-kicker">FILING & REVISION PREVIEW</span><h3>Research activity</h3></div><FileText size={16} /></div><div className="activity-row"><span>EPS estimate revision</span><b>Stable <small>illustrative</small></b><span>Analyst rating changes</span><b>No sample change</b></div></SpotlightCard></div>;
  if (tab === "News") return <NewsPanel />;
  return <div className="technical-layout"><SpotlightCard className="technical-main"><div className="card-heading"><div><span className="section-kicker">PRICE CONTEXT</span><h3>Technical snapshot · {ticker.symbol}</h3></div><span className="sample-tag">ILLUSTRATIVE</span></div><div className="technical-score"><strong>{ticker.strength}</strong><span>/ 100 sample strength</span><div className="strength-meter"><span style={{ width: `${ticker.strength}%` }} /></div></div><div className="technical-indicators"><div><span>Trend context</span><b>Mixed to constructive</b><small>Sample reading</small></div><div><span>Relative strength</span><b>Near peer median</b><small>Fixture only</small></div><div><span>Volatility band</span><b>Moderate</b><small>Not a forecast</small></div></div></SpotlightCard><SpotlightCard className="research-panel technical-note"><span className="section-kicker">METHODOLOGY NOTE</span><h3>Illustrative inputs only</h3><p>Technical labels and scores here exist to demonstrate the research layout. They are not derived from market data or the production MarketLens calculation engine.</p></SpotlightCard></div>;
}

function NewsPanel() {
  const [sentiment, setSentiment] = useState("All sentiment");
  const headlines = companyResearchFixtures.headlines.filter(([, , , label]) => sentiment === "All sentiment" || label === sentiment);
  return <SpotlightCard className="research-panel news-panel"><div className="card-heading"><div><span className="section-kicker">HEADLINES & SENTIMENT</span><h3>Recent coverage · sample headlines</h3></div><div className="news-filter"><Filter size={13} /><select aria-label="Filter headline sentiment" value={sentiment} onChange={(event) => setSentiment(event.target.value)}><option>All sentiment</option><option>Neutral</option><option>Mixed</option></select></div></div><div className="news-list">{headlines.map(([title, source, time, label]) => <ExpandableResearchCard key={title} title={title} subtitle={`${source} · ${time} ago · simulated fixture`} preview={<><span className="news-source-mark">{source.slice(0, 1)}</span><span className="news-item-copy"><strong>{title}</strong><small>{source} · {time} ago · simulated fixture</small></span><span className="sentiment-neutral">{label}</span></>} className="news-item-expand"><p>This headline is generic illustrative content and does not describe a real company event or publication.</p><p>Sentiment label: <b>{label}</b> · Source label: <b>{source}</b></p></ExpandableResearchCard>)}</div><p className="table-caption">Headline wording is intentionally generic and does not describe real news.</p></SpotlightCard>;
}

function EngineResearchWorkspace({ selectedTicker, onNavigate }: CommonProps) {
  const [tab, setTab] = useState("Overview");
  const [requestState, setRequestState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [research, setResearch] = useState<ApiEnvelope<ResearchData> | null>(null);
  const [analysis, setAnalysis] = useState<ApiEnvelope<TechnicalAnalysisData> | null>(null);
  const [news, setNews] = useState<ApiEnvelope<NewsEventsData> | null>(null);
  const tabs = ["Overview", "Financials", "Analysts & events", "News", "Technical"];

  useEffect(() => {
    const controller = new AbortController();
    setRequestState("loading"); setError(""); setResearch(null); setAnalysis(null); setNews(null);
    const handleError = (cause: unknown) => {
      if (controller.signal.aborted) return;
      setError(cause instanceof ApiRequestError ? cause.message : "The Python research service could not complete this request.");
      setRequestState("error");
    };
    if (tab === "Technical") {
      fetchTechnicalAnalysis(selectedTicker.symbol, controller.signal).then((value) => { setAnalysis(value); setRequestState("ready"); }).catch(handleError);
    } else if (tab === "News") {
      fetchNewsEvents(selectedTicker.symbol, controller.signal).then((value) => { setNews(value); setRequestState("ready"); }).catch(handleError);
    } else {
      fetchCompanyResearch(selectedTicker.symbol, controller.signal).then((value) => { setResearch(value); setRequestState("ready"); }).catch(handleError);
    }
    return () => controller.abort();
  }, [tab, selectedTicker.symbol, retry]);

  const activeEnvelope = tab === "Technical" ? analysis : tab === "News" ? news : research;
  const panel = requestState === "loading"
    ? <div className="workspace-state" role="status"><span className="loading-ring" /> Running existing Python research functions on deterministic synthetic inputs…</div>
    : requestState === "error"
      ? <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18} /><div><b>Python research response unavailable</b><span>{error}</span></div><button className="quiet-button" onClick={() => setRetry((value) => value + 1)}>Retry local request</button></div>
      : tab === "Technical" && analysis?.data ? <EngineTechnicalPanel data={analysis.data} />
        : tab === "News" && news?.data ? <EngineNewsPanel data={news.data} />
          : research?.data ? tab === "Analysts & events" ? <EngineAnalystPanel data={research.data} /> : <EngineFundamentalsPanel data={research.data} />
            : <div className="workspace-state" role="status">No research fields were returned by the local Python adapter.</div>;

  return <div className="functional-workspace">
    <WorkspaceHeading kicker="COMPANY RESEARCH" title="One company. A fuller picture." description="Existing Python normalizers and analysis functions, exercised with deterministic offline inputs." />
    <FixtureBanner>Python engine demonstration · all provider-shaped inputs and resulting values are synthetic test fixtures, not current or verified research.</FixtureBanner>
    <div className="research-company-header"><div className="ticker-avatar">{selectedTicker.symbol.slice(0, 1)}</div><div className="research-company-name"><span>{selectedTicker.exchange} · {selectedTicker.sector} · {selectedTicker.industry}</span><h2>{selectedTicker.name} <small>{selectedTicker.symbol}</small></h2><p><span className="fixture-indicator-dot" /> Python engine snapshot · local only</p></div><button className="outline-button" onClick={() => onNavigate("overview")}>Market overview <ArrowDownRight size={14} /></button></div>
    <WorkspaceTabs label="Company research sections" items={tabs} value={tab} onChange={setTab} />
    <div className="discovery-summary-row"><div><span className="section-kicker">{tab.toUpperCase()} · {selectedTicker.symbol}</span><h2>{tab === "Overview" ? "Business & valuation" : tab}</h2></div><span className="sample-tag">PYTHON ENGINE · SYNTHETIC INPUTS</span></div>
    {activeEnvelope?.status === "partial" && <div className="workspace-fixture-note" role="status">Partial Python-engine result. Missing fields: {activeEnvelope.missing_fields.join(", ") || activeEnvelope.warnings.join(" ")}</div>}
    {activeEnvelope?.stale && <div className="workspace-fixture-note" role="status">Showing the last successful company-research response; the data is marked stale.</div>}
    {activeEnvelope?.provenance && <p className="table-caption">Calculation provenance: {activeEnvelope.provenance} · as of {activeEnvelope.as_of ?? "not timestamped"}</p>}
    {panel}
  </div>;
}

function EngineFundamentalsPanel({ data }: { data: ResearchData }) {
  return <>
    <div className="research-metric-grid">{data.fundamentals.map((metric) => <ExpandableResearchCard className="research-metric" key={metric.label} title={metric.label} subtitle={`${data.symbol} · market_lens.research normalizer`} preview={<><span>{metric.label}</span><strong>{metric.display_value}</strong><small>{metric.context}</small></>}><div className="expandable-fact-grid"><div><span>Normalized display</span><b>{metric.display_value}</b></div><div><span>Raw synthetic input</span><b>{metric.raw_value === null ? "Unavailable" : metric.raw_value.toLocaleString()}</b></div></div><p>This result comes from the existing Python fundamentals presentation normalizer. The input is a local synthetic fixture.</p></ExpandableResearchCard>)}</div>
    <div className="research-columns"><SpotlightCard className="research-panel"><div className="card-heading"><div><span className="section-kicker">BUSINESS SNAPSHOT</span><h3>Validated fixture identity</h3></div><BarChart3 size={16} /></div><div className="context-list"><div><span>Company</span><b>{data.name}</b></div><div><span>Sector</span><b>{data.sector}</b></div><div><span>Industry</span><b>{data.industry}</b></div><div><span>Normalization source</span><b>Python engine snapshot</b></div></div><p className="table-caption">Identity fields are local directory fixtures and are not independently verified company data.</p></SpotlightCard>
      <SpotlightCard className="research-panel"><div className="card-heading"><div><span className="section-kicker">QUARTERLY FINANCIALS</span><h3>Normalized statement rows</h3></div><span className="sample-tag">SYNTHETIC INPUTS</span></div><div className="financial-table engine-financial-table"><div><span>Period</span><span>Revenue ($B)</span><span>Operating income ($B)</span><span>Net income ($B)</span><span>Diluted EPS</span></div>{data.quarterly_financials.map((row) => <div key={row.period}><b>{row.period}</b><span>{formatNumber(row.revenue)}</span><span>{formatNumber(row.operating_income)}</span><span>{formatNumber(row.net_income)}</span><span>{formatNumber(row.diluted_eps)}</span></div>)}</div><p className="table-caption">Rows and periods were passed through the original quarterly statement normalizer. Missing values remain empty.</p></SpotlightCard></div>
  </>;
}

function EngineAnalystPanel({ data }: { data: ResearchData }) {
  const targets = data.analyst_targets;
  return <div className="research-columns"><SpotlightCard className="research-panel analyst-panel"><div className="card-heading"><div><span className="section-kicker">PYTHON ANALYST NORMALIZATION</span><h3>Consensus fixture</h3></div><TrendingUp size={16} /></div><div className="target-range"><span>Existing analytics consensus</span><strong>{data.analyst_consensus.rating ?? "Unavailable"}</strong><small>{data.analyst_consensus.count} synthetic ratings · score {formatNumber(data.analyst_consensus.score)}</small></div>{targets && <div className="expandable-fact-grid"><div><span>Mean target</span><b>{formatMoney(targets.mean)}</b></div><div><span>Median target</span><b>{formatMoney(targets.median)}</b></div><div><span>Target range</span><b>{formatMoney(targets.low)} – {formatMoney(targets.high)}</b></div><div><span>Implied upside</span><b>{targets.upside_percent === null ? "Unavailable" : `${targets.upside_percent.toFixed(2)}%`}</b></div></div>}<ExpandableResearchCard title="Analyst distribution details" subtitle={`${data.symbol} · original Python normalizers`} preview={<span>{data.recommendation_distribution.reduce((sum, row) => sum + row.count, 0)} total synthetic ratings</span>} className="analyst-detail-trigger"><div className="rating-bars">{data.recommendation_distribution.map((row) => <div key={row.rating}><span>{row.rating}</span><div><i className={`bar-${row.rating.toLowerCase().replaceAll(" ", "-")}`} style={{ width: `${Math.min(100, row.count * 7)}%` }} /></div><b>{row.count}</b></div>)}</div><p className="table-caption">Counts are synthetic provider-shaped input normalized by market_lens.research and market_lens.analytics.</p></ExpandableResearchCard></SpotlightCard>
    <SpotlightCard className="research-panel"><div className="card-heading"><div><span className="section-kicker">EVENT FIXTURES</span><h3>Sample calendar</h3></div><CalendarDays size={16} /></div><div className="timeline">{data.events.map((event) => <ExpandableResearchCard key={event.title} title={event.title} subtitle={`${event.date_label} · synthetic event fixture`} preview={<span>{event.detail}</span>} className="event-detail-trigger"><p>{event.detail}</p><p>No real event calendar is connected.</p></ExpandableResearchCard>)}</div></SpotlightCard>
    <SpotlightCard className="research-panel wide-panel"><div className="card-heading"><div><span className="section-kicker">EPS ESTIMATE REVISIONS</span><h3>Normalized revision counts</h3></div><FileText size={16} /></div><div className="activity-row">{data.eps_revisions.map((row) => <div key={row.period}><span>{row.period}</span><b>↑ {row.up_last_30days ?? "—"} · ↓ {row.down_last_30days ?? "—"}</b></div>)}</div><p className="table-caption">Revision fixture values are output by the original Python presentation normalizer.</p></SpotlightCard></div>;
}

function EngineTechnicalPanel({ data }: { data: TechnicalAnalysisData }) {
  const indicatorLabels: [string, string][] = [["Last sample close", "last"], ["Daily change (%)", "change"], ["20-session SMA", "sma20"], ["50-session SMA", "sma50"], ["200-session SMA", "sma200"], ["RSI · 14", "rsi"], ["MACD", "macd"], ["Annualized realized volatility", "hist_vol"], ["Current drawdown (%)", "current_drawdown"], ["Beta vs fixture benchmark", "beta"]];
  return <div className="technical-layout"><SpotlightCard className="technical-main"><div className="card-heading"><div><span className="section-kicker">EXISTING PYTHON CALCULATION</span><h3>{data.rating} · {data.symbol}</h3></div><span className="sample-tag">{data.observations} SYNTHETIC OBSERVATIONS</span></div><div className="technical-score"><strong>{data.technical_rating}</strong><span>{data.rating_source}</span></div><div className="technical-indicators">{indicatorLabels.map(([label, key]) => <div key={key}><span>{label}</span><b>{formatNumber(data.indicators[key] ?? null)}</b><small>Python engine result</small></div>)}</div><p className="table-caption">{data.trend_state} · analyst count {data.analyst_count}; realized-volatility observations {data.hist_vol_observations}; beta observations {data.beta_observations}.</p><ExpandableResearchCard title="Rating calculation checks" subtitle={`${data.symbol} · original analytics.analyze result`} preview={<span>{data.constructive_checks} constructive · {data.caution_checks} caution checks</span>}><div className="context-list">{data.rating_checks.map((check) => <div key={`${check.side}-${check.label}`}><span>{check.side}</span><b>{check.passed === null ? "Unavailable" : check.passed ? "Pass" : "No pass"} · {check.label}</b></div>)}</div><p>These checks are returned by the existing Python function. No financial rule was recreated in React.</p></ExpandableResearchCard></SpotlightCard><SpotlightCard className="research-panel technical-note"><span className="section-kicker">NUMERICAL PROVENANCE</span><h3>Unmodified calculation path</h3><p>{data.disclosure}</p><p>3-month excess return: {formatPercent(data.returns["3m"]?.excess ?? null)} · paired benchmark observations: {data.returns["3m"]?.observations ?? "Unavailable"}.</p><p>Expected-move source: {data.move_source}.</p></SpotlightCard></div>;
}

function EngineNewsPanel({ data }: { data: NewsEventsData }) {
  const [sentiment, setSentiment] = useState("All sentiment");
  const headlines = data.headlines.filter((item) => sentiment === "All sentiment" || item.sentiment === sentiment);
  return <><SpotlightCard className="research-panel news-panel"><div className="card-heading"><div><span className="section-kicker">PYTHON NEWS CLASSIFIER · SYNTHETIC TEXT</span><h3>Headline relevance and sentiment</h3></div><div className="news-filter"><Filter size={13} /><select aria-label="Filter headline sentiment" value={sentiment} onChange={(event) => setSentiment(event.target.value)}><option>All sentiment</option><option>Bullish</option><option>Bearish</option><option>Neutral</option></select></div></div><div className="news-list">{headlines.map((item) => <ExpandableResearchCard key={item.title} title={item.title} subtitle={`${item.publisher} · synthetic text · ${item.published_at}`} preview={<><span className="news-source-mark">{item.sentiment.slice(0, 1)}</span><span className="news-item-copy"><strong>{item.title}</strong><small>{item.topic} · {item.confidence} confidence</small></span><span className={`sentiment-neutral sentiment-${item.sentiment.toLowerCase()}`}>{item.sentiment}</span></>} className="news-item-expand"><div className="expandable-fact-grid"><div><span>Issuer relevance</span><b>{item.issuer_relevant ? "Relevant to selected fixture" : "Unclear / unrelated"}</b></div><div><span>Classifier explanation</span><b>{item.reason}</b></div><div><span>Bull score</span><b>{item.bull_score.toFixed(2)}</b></div><div><span>Bear score</span><b>{item.bear_score.toFixed(2)}</b></div></div><p>The existing market_lens.news classifier processed this explicitly synthetic headline text. It is not an actual article.</p></ExpandableResearchCard>)}</div><p className="table-caption">{data.disclosure}</p></SpotlightCard><div className="event-list">{data.events.map((event) => <SpotlightCard className="event-row" key={event.title}><div className="event-date"><CalendarDays size={16} /><b>{event.date_label}</b></div><div><h3>{event.title}</h3><p>{event.detail}</p></div><span className="event-status">SYNTHETIC EVENT</span></SpotlightCard>)}</div></>;
}

function formatNumber(value: number | null): string { return value === null || !Number.isFinite(value) ? "Unavailable" : value.toLocaleString(undefined, { maximumFractionDigits: 3 }); }
function formatMoney(value: number | null | undefined): string { return value === null || value === undefined ? "Unavailable" : `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }
function formatPercent(value: number | null): string { return value === null ? "Unavailable" : `${(value * 100).toFixed(2)}%`; }

function FixtureWatchlistWorkspace({ selectedSymbol, watchlist, onSelectTicker, onAddTicker, onRemoveTicker, onNavigate, dataMode = "fixtures", persistent = false }: CommonProps & { onAddTicker: (symbol: string) => Promise<boolean>; onRemoveTicker: (symbol: string) => Promise<boolean>; dataMode?: Exclude<DataMode, "public">; persistent?: boolean }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("Symbol A–Z");
  const [notice, setNotice] = useState("");
  const [summaryResponse, setSummaryResponse] = useState<ApiEnvelope<WatchlistSummaryData> | null>(null);
  const [summaryError, setSummaryError] = useState("");
  const [summaryRetry, setSummaryRetry] = useState(0);
  const watchlistKey = watchlist.join(",");
  useEffect(() => {
    if (dataMode !== "fastapi" || !watchlistKey) { setSummaryResponse(null); setSummaryError(""); return; }
    const controller = new AbortController();
    setSummaryResponse(null); setSummaryError("");
    fetchWatchlistSummaries(watchlistKey.split(","), controller.signal).then(setSummaryResponse).catch((cause: unknown) => {
      if (!controller.signal.aborted) setSummaryError(cause instanceof ApiRequestError ? cause.message : "The local Python summary could not complete the request.");
    });
    return () => controller.abort();
  }, [dataMode, watchlistKey, summaryRetry]);
  const available = tickerFixtures.filter((item) => !watchlist.includes(item.symbol) && `${item.symbol} ${item.name}`.toLowerCase().includes(query.toLowerCase()));
  const list = [...watchlist].map((symbol) => tickerFor(symbol)).sort((a, b) => sort === "Company name" ? a.name.localeCompare(b.name) : sort === "Daily move" ? moveValue(b.change) - moveValue(a.change) : a.symbol.localeCompare(b.symbol));
  async function add(symbol: string) { if (!await onAddTicker(symbol)) return; setQuery(""); setNotice(persistent ? symbol + " saved to your account watchlist." : symbol + " added to this browser-session watchlist."); }
  return <div className="functional-workspace">
    <WorkspaceHeading kicker="YOUR WATCHLIST" title="Keep your research close." description="A locally managed sample list to revisit companies and continue into research." />
    <FixtureBanner>{persistent ? "Your ticker symbols are saved to your signed-in account and protected by database row-level security. Any displayed market or research values remain illustrative or synthetic." : dataMode === "fastapi" ? "The watchlist remains temporary to this browser session. Read-only company summaries come from the Python demo over synthetic inputs; nothing is saved to an account." : "Watchlist state is temporary to this browser session. It is not saved to an account or synced between devices."}</FixtureBanner>
    <div className="watchlist-toolbar"><label className="directory-search"><Search size={16} /><input aria-label="Search tickers to add" placeholder="Find a fixture ticker to add…" value={query} onChange={(event) => setQuery(event.target.value)} /><kbd>{available.length} available</kbd></label><label className="sort-control">Sort by<select aria-label="Sort watchlist" value={sort} onChange={(event) => setSort(event.target.value)}><option>Symbol A–Z</option><option>Company name</option><option>Daily move</option></select><ChevronDown size={13} /></label></div>
    {query && <div className="ticker-suggestion-list" role="listbox" aria-label="Available fixture tickers">{available.map((item) => <button key={item.symbol} role="option" aria-selected="false" onClick={() => add(item.symbol)}><b>{item.symbol}</b><span>{item.name}</span><span>{item.sector} · illustrative</span><span className="suggest-add">+ Add</span></button>)}{!available.length && <span className="table-empty">No unpinned fixture match.</span>}</div>}
    {notice && <div className="inline-success" role="status"><ShieldCheck size={14} />{notice}<button onClick={() => setNotice("")} aria-label="Dismiss notification">×</button></div>}
    <div className="discovery-summary-row watchlist-summary"><div><span className="section-kicker">{persistent ? "SAVED WATCHLIST" : "GUEST WATCHLIST"}</span><h2>{list.length} {list.length === 1 ? "ticker" : "tickers"}</h2></div><span className="session-only-label">{persistent ? <><ShieldCheck size={13} /> Account synced</> : <><Clock3 size={13} /> Browser session only</>}</span></div>
    {dataMode === "fastapi" && summaryError && <div className="workspace-state workspace-error" role="alert"><CircleHelp size={18} /><div><b>Python watchlist summaries unavailable</b><span>{summaryError}</span></div><button className="quiet-button" onClick={() => setSummaryRetry((value) => value + 1)}>Retry local request</button></div>}
    {dataMode === "fastapi" && summaryResponse?.status === "partial" && <p className="table-caption" role="status">{summaryResponse.warnings.join(" ")}</p>}
    {dataMode === "fastapi" && summaryResponse?.stale && <p className="table-caption" role="status">Showing the last successful Watchlist summary; it is marked stale.</p>}
    <SpotlightCard className="data-table-card"><div className="directory-table watchlist-table" role="table" aria-label={persistent ? "Saved account watchlist" : "Session watchlist"}><div className="directory-row directory-head" role="row"><span>COMPANY</span><span>SECTOR</span><span>{dataMode === "fastapi" ? "PYTHON SAMPLE CLOSE" : "SAMPLE CLOSE"}</span><span>DAILY MOVE</span></div>{list.map((item) => <WatchlistItemRow key={item.symbol} item={item} summary={summaryResponse?.data?.summaries.find((row) => row.symbol === item.symbol)} dataMode={dataMode} summaryLoading={!summaryResponse && !summaryError && dataMode === "fastapi"} selected={selectedSymbol === item.symbol} onSelectTicker={onSelectTicker} onResearch={() => { onSelectTicker(item.symbol); onNavigate("research"); }} onRemove={async () => { if (await onRemoveTicker(item.symbol)) setNotice(persistent ? item.symbol + " removed from your account watchlist." : item.symbol + " removed from your session watchlist."); }} />)}{!list.length && <div className="table-empty">Your session list is empty. Search above to add an illustrative ticker.</div>}</div><div className="table-footnote"><span>{dataMode === "fastapi" ? "Python-calculated fields use synthetic inputs only." : "All quote fields are sample values."}</span><span>{persistent ? "Only ticker and exchange identifiers are stored." : "Guest watchlist is temporary in this browser session."}</span></div></SpotlightCard>
    <div className="workspace-help-note"><Bookmark size={14} /><span>{persistent ? "Your account list syncs through Supabase Auth and owner-scoped database policies." : "Guest selections stay in this browser session and are never uploaded automatically."}</span></div>
  </div>;
}

export function WatchlistWorkspace(props: CommonProps & { onAddTicker: (symbol: string) => Promise<boolean>; onRemoveTicker: (symbol: string) => Promise<boolean>; dataMode?: DataMode; persistent?: boolean; accountLoading?: boolean }) {
  return props.dataMode === "public" ? <PublicWatchlistWorkspace {...props} /> : <FixtureWatchlistWorkspace {...props} dataMode={props.dataMode ?? "fixtures"} persistent={props.persistent} />;
}

function PublicWatchlistWorkspace({ selectedSymbol, watchlist, onSelectTicker, onAddTicker, onRemoveTicker, onNavigate, persistent = false }: CommonProps & { onAddTicker: (symbol: string) => Promise<boolean>; onRemoveTicker: (symbol: string) => Promise<boolean>; persistent?: boolean }) {
  const [query, setQuery] = useState("");
  const suggestions = tradingViewTickerSymbols.filter((symbol) => !watchlist.includes(symbol) && symbol.includes(query.trim().toUpperCase()));
  return <div className="functional-workspace">
    <WorkspaceHeading kicker="YOUR WATCHLIST" title="Keep your research close." description={persistent ? "Manage the symbols saved to your account." : "Manage a temporary list of exchange-qualified chart symbols in this browser session."} badge={persistent ? "ACCOUNT WATCHLIST" : "PUBLIC VIEW · GUEST SESSION"} />
    <div className="public-data-note"><ShieldCheck size={16} /><span>{persistent ? "Only ticker and exchange identifiers are stored in your account. Company names, quotes, sector data, and ratings are not provided in public mode." : "Guest symbols stay temporary in this browser session. Company names, quotes, sector data, and ratings are not provided in public mode."}</span></div>
    <div className="watchlist-toolbar"><label className="directory-search"><Search size={16} /><input aria-label="Search tickers to add" placeholder="Find a supported ticker…" value={query} onChange={(event) => setQuery(event.target.value)} /><kbd>{suggestions.length} available</kbd></label></div>
    {query && <div className="ticker-suggestion-list" role="listbox" aria-label="Exchange-qualified chart tickers">{suggestions.map((symbol) => <button key={symbol} role="option" aria-selected="false" onClick={async () => { if (await onAddTicker(symbol)) setQuery(""); }}><b>{symbol}</b><span>{symbol}</span><span>TradingView chart symbol</span><span className="suggest-add">+ Add</span></button>)}{!suggestions.length && <span className="table-empty">No available configured symbol matches.</span>}</div>}
    <div className="discovery-summary-row watchlist-summary"><div><span className="section-kicker">{persistent ? "ACCOUNT WATCHLIST" : "GUEST WATCHLIST"}</span><h2>{watchlist.length} {watchlist.length === 1 ? "ticker" : "tickers"}</h2></div><span className="session-only-label">{persistent ? <><ShieldCheck size={13} /> Account synced</> : <><Clock3 size={13} /> Browser session only</>}</span></div>
    <SpotlightCard className="public-watchlist-card"><div className="public-watchlist-list">{watchlist.map((symbol) => <div className="public-watchlist-row" key={symbol}><button className="directory-company" onClick={() => onSelectTicker(symbol)} aria-current={selectedSymbol === symbol ? "true" : undefined}><span className="directory-avatar">{symbol.slice(0, 1)}</span><span><b>{symbol}</b><small>Exchange-qualified chart symbol</small></span></button><span className="unavailable-field">Quote and company research unavailable</span><div><button className="row-research" onClick={() => { onSelectTicker(symbol); onNavigate("research"); }}>Research <ArrowDownRight size={13} /></button><button className="remove-ticker" onClick={() => void onRemoveTicker(symbol)} aria-label={"Remove " + symbol + " from watchlist"}>Remove</button></div></div>)}{!watchlist.length && <div className="table-empty">Your session watchlist is empty.</div>}</div></SpotlightCard>
  </div>;
}

function WatchlistItemRow({ item, summary, dataMode, summaryLoading, selected, onSelectTicker, onResearch, onRemove }: {
  item: ReturnType<typeof tickerFor>;
  summary?: WatchlistSummaryData["summaries"][number];
  dataMode: "fixtures" | "fastapi";
  summaryLoading: boolean;
  selected: boolean;
  onSelectTicker: (symbol: string) => void;
  onResearch: () => void;
  onRemove: () => void;
}) {
  const companyName = dataMode === "fastapi" ? summary?.name ?? item.symbol : item.name;
  const sector = dataMode === "fastapi" ? summary?.sector ?? "Unavailable" : item.sector;
  const industry = dataMode === "fastapi" ? summary?.industry ?? "Unavailable" : item.industry;
  const close = dataMode === "fastapi" ? summary?.sample_close === null || summary?.sample_close === undefined ? summaryLoading ? "Loading…" : "Unavailable" : `$${summary.sample_close.toFixed(2)}` : `$${item.price}`;
  const change = dataMode === "fastapi" ? summary?.sample_change_percent === null || summary?.sample_change_percent === undefined ? summaryLoading ? "Loading…" : "Unavailable" : `${summary.sample_change_percent >= 0 ? "+" : ""}${summary.sample_change_percent.toFixed(2)}%` : item.change;
  const tone = dataMode === "fastapi" ? summary?.sample_change_percent !== undefined && summary.sample_change_percent !== null && summary.sample_change_percent >= 0 ? "tone-up" : "tone-down" : item.changeTone === "up" ? "tone-up" : "tone-down";
  return <div className={`directory-row ${selected ? "directory-row-selected" : ""}`} role="row" key={item.symbol}>
    <button className="directory-company" onClick={() => onSelectTicker(item.symbol)}><span className="directory-avatar">{item.symbol.slice(0, 1)}</span><span><b>{item.symbol}</b><small>{companyName}</small></span></button>
    <span className="directory-industry"><b>{sector}</b><small>{industry}</small></span>
    <span className="directory-cap">{close}<small>{dataMode === "fastapi" ? "Python sample result" : "illustrative close"}</small></span>
    <span className={`watch-change ${tone}`}>{change}</span>
    <div className="watchlist-actions">
      <ExpandableResearchCard title={`${item.symbol} · ${companyName}`} subtitle={`${sector} · ${industry}`} preview={<span>{dataMode === "fastapi" ? "View Python summary" : "View sample company details"}</span>} className="watchlist-detail-trigger">
        {dataMode === "fastapi" ? summary ? <><div className="expandable-fact-grid"><div><span>Python sample close</span><b>{close}</b></div><div><span>Python sample move</span><b>{change}</b></div><div><span>Technical rating</span><b>{summary.technical_rating}</b></div><div><span>Trend context</span><b>{summary.trend_state}</b></div><div><span>Sector · industry fixture identity</span><b>{sector} · {industry}</b></div></div><p className="table-caption">{summaryResponseDisclosure(summary)}</p></> : <p>{summaryLoading ? "Waiting for the local Python API summary." : "The Python summary is unavailable; no frontend quote fallback is shown."}</p> : <div className="expandable-fact-grid"><div><span>Sample price</span><b>${item.price}</b></div><div><span>Sample move</span><b>{item.change}</b></div><div><span>Industry</span><b>{item.industry}</b></div><div><span>Sample strength</span><b>{item.strength} / 100</b></div></div>}
        <button type="button" className="outline-button expandable-action" onClick={onResearch}>Open Company Research <ArrowDownRight size={14} /></button>
      </ExpandableResearchCard>
      <button className="row-research" aria-label={`Research ${item.symbol}`} onClick={onResearch}>Research <ArrowDownRight size={13} /></button>
      <button className="remove-ticker" onClick={onRemove} aria-label={`Remove ${item.symbol} from watchlist`}>Remove</button>
    </div>
  </div>;
}

function summaryResponseDisclosure(_: WatchlistSummaryData["summaries"][number]) {
  return "Existing Python technical analysis over synthetic inputs. This is not live market data or account-persisted information.";
}

function moveValue(value: string) { return parseFloat(value.replace("−", "-")) || 0; }


