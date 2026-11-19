import { resolveApiBaseUrl } from "../releaseFeatures";

export type ApiStatus = "ok" | "partial" | "unavailable" | "rate_limited" | "failed" | "invalid";
export type ApiEnvelope<T> = {
  data: T | null;
  status: ApiStatus;
  source: "synthetic-fixtures" | "python-engine-snapshot" | "sec-edgar";
  freshness: "simulated" | "live" | "cached";
  as_of?: string | null;
  provenance?: string | null;
  missing_fields: string[];
  warnings: string[];
  stale?: boolean;
};

export type ApiMarketIndex = { name: string; symbol: string; value: string; change: string; tone: "up" | "down"; series: number[] };
export type OverviewData = { markets: ApiMarketIndex[]; sector_activity: { name: string; value: number }[]; disclosure: string };
export type ApiDiscoveryCompany = {
  symbol: string; name: string; exchange: string; sector: string; industry: string;
  price: string; change: string; change_tone: "up" | "down"; series: number[];
  strength: number; range: "1M"; market_cap: string; rating: "Positive" | "Balanced" | "Cautious";
  classification_label: "simulated classification";
};
export type DiscoveryData = {
  sectors: string[];
  industries: { name: string; sector: string; company_count: number }[];
  companies: ApiDiscoveryCompany[];
  selected_sector: string | null;
  selected_industry: string | null;
  query: string;
  disclosure: string;
};
export type TickerSearchData = { query: string; results: { symbol: string; name: string; exchange: string; sector: string; industry: string }[] };
export type ChartData = { symbol: string; range: ChartRange; interval: ChartResolution; bars: { time: string; open: number; high: number; low: number; close: number; volume: number }[]; label: string };
export type ChartRange = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";
export type ChartResolution = "15m" | "30m" | "1h" | "2h" | "12h" | "1d";
export const chartResolutions: readonly ChartResolution[] = ["15m", "30m", "1h", "2h", "12h", "1d"];
export type DiscoveryCalendarData = { kind: "earnings" | "ipos"; window_days: number; items: { symbol: string; name: string; date_label: string; title: string; detail: string }[]; disclosure: string };
export type WatchlistSummaryData = { symbols: string[]; summaries: { symbol: string; name: string; sector: string; industry: string; sample_close: number | null; sample_change_percent: number | null; technical_rating: string; trend_state: string }[]; disclosure: string };
export type TechnicalAnalysisData = {
  symbol: string; name: string; indicators: Record<string, number | null>; move_source: string; trend_state: string;
  rating: string; rating_source: string; technical_rating: string; analyst_rating: string | null; analyst_count: number;
  analyst_score: number | null; analyst_period: string | null; constructive_checks: number; caution_checks: number;
  rating_checks_complete: boolean; rating_checks: { side: "Constructive" | "Caution"; label: string; passed: boolean | null }[];
  returns: Record<string, Record<string, number | null>>; observations: number; hist_vol_observations: number;
  drawdown_observations: number; beta_observations: number; as_of: string; disclosure: string;
};
export type ResearchData = {
  symbol: string; name: string; exchange: string; sector: string; industry: string;
  fundamentals: { label: string; display_value: string; raw_value: number | null; context: string }[];
  quarterly_financials: { period: string; revenue: number | null; operating_income: number | null; net_income: number | null; diluted_eps: number | null }[];
  analyst_targets: { current: number | null; high: number | null; low: number | null; mean: number | null; median: number | null; upside_percent: number | null } | null;
  analyst_consensus: { rating: string | null; count: number; score: number | null; period: string | null };
  recommendation_distribution: { rating: string; count: number }[];
  eps_revisions: { period: string; up_last_7days: number | null; up_last_30days: number | null; down_last_7_days: number | null; down_last_30days: number | null }[];
  events: { date_label: string; title: string; detail: string }[]; disclosure: string; as_of: string;
};
export type NewsEventsData = {
  symbol: string; headlines: { title: string; publisher: string; published_at: string; sentiment: "Bullish" | "Bearish" | "Neutral"; confidence: "High" | "Medium" | "Low"; reason: string; issuer_relevant: boolean; bull_score: number; bear_score: number; topic: string }[];
  events: { date_label: string; title: string; detail: string }[]; disclosure: string; as_of: string;
};
export type SecCompanyReport = {
  identity: { cik: string; ticker: string; name: string; exchange: string | null; identity_source: "sec_company_tickers" | "approved_fixture" };
  facts: { field: string; taxonomy: string; tag: string; label: string; value: number; original_value: string; unit: string; currency: string | null; period_start: string | null; period_end: string; fiscal_year: number | null; fiscal_period: string | null; form: string; filed: string; accession_number: string; filing_url: string | null; latest_reported_version: boolean }[];
  annual_periods?: SecStatementPeriod[];
  quarterly_periods?: SecStatementPeriod[];
  ytd_periods?: SecStatementPeriod[];
  filings: { cik: string; accession_number: string; form: string; filing_date: string; report_period: string | null; primary_document: string | null; filing_url: string | null }[];
  missing_fields: string[]; source: string; live_data: boolean; status: "ok" | "partial"; as_of: string | null; warnings: string[];
};
export type SecStatementMetric = {
  field: string; taxonomy: string; tag: string; label: string; value: number; original_value: string;
  unit: string; currency: string | null; period_start: string | null; period_end: string;
  duration_days: number | null; form: string; filed: string; accession_number: string;
  filing_url: string | null; comparison_percent: number | null; comparison_period_end: string | null;
  comparison_value?: string | null; comparison_filed?: string | null; comparison_form?: string | null;
  comparison_accession_number?: string | null; comparison_filing_url?: string | null;
};
export type SecStatementPeriod = {
  fiscal_year: number | null; fiscal_period: string | null; period_type: "annual" | "quarterly" | "ytd";
  period_start: string | null; period_end: string; metrics: Record<string, SecStatementMetric[]>;
};
export type SecDirectoryCompany = { ticker: string; name: string; cik: string; exchange: string | null };
export type SecDirectoryData = {
  companies: SecDirectoryCompany[]; total: number; limit: number; offset: number; query: string;
  exchange: string | null; available_exchanges: string[]; disclosure: string;
};
export type SecFilingActivity = {
  cik: string; ticker: string; company_name: string; exchange: string | null; sic: string | null;
  sic_description: string | null; form: string; filing_date: string; report_date: string | null;
  accession_number: string; primary_document: string | null; filing_url: string | null; items: string | null;
};
export type SecFilingsData = {
  ticker: string; company_name: string; cik: string; exchange: string | null; sic: string | null;
  sic_description: string | null; filings: SecFilingActivity[]; forms: string[]; disclosure: string;
};

export class ApiRequestError extends Error {
  constructor(message: string, readonly status: ApiStatus = "failed", readonly httpStatus?: number) {
    super(message);
    this.name = "ApiRequestError";
  }
}

const baseUrl = resolveApiBaseUrl();
const requestTimeoutMs = 5_000;
const secRequestTimeoutMs = 30_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function isEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return isRecord(value)
    && ["ok", "partial", "unavailable", "rate_limited", "failed", "invalid"].includes(String(value.status))
    && ["synthetic-fixtures", "python-engine-snapshot", "sec-edgar"].includes(String(value.source))
    && ["simulated", "live", "cached"].includes(String(value.freshness))
    && Array.isArray(value.warnings)
    && (value.stale === undefined || typeof value.stale === "boolean")
    && (value.missing_fields === undefined || Array.isArray(value.missing_fields))
    && (value.data === null || isRecord(value.data));
}
function isOverviewData(value: unknown): value is OverviewData {
  return isRecord(value) && Array.isArray(value.markets) && Array.isArray(value.sector_activity)
    && value.sector_activity.every((item) => isRecord(item) && typeof item.name === "string" && typeof item.value === "number" && item.value >= 0 && item.value <= 100)
    && typeof value.disclosure === "string"
    && value.markets.every((row) => isRecord(row) && typeof row.name === "string" && typeof row.symbol === "string" && typeof row.value === "string" && typeof row.change === "string" && (row.tone === "up" || row.tone === "down") && Array.isArray(row.series) && row.series.every((point) => typeof point === "number" && Number.isFinite(point)));
}
function isDiscoveryCompany(value: unknown): value is ApiDiscoveryCompany {
  return isRecord(value) && ["symbol", "name", "exchange", "sector", "industry", "price", "change", "market_cap"].every((key) => typeof value[key] === "string")
    && (value.change_tone === "up" || value.change_tone === "down")
    && Array.isArray(value.series) && value.series.every((point) => typeof point === "number" && Number.isFinite(point))
    && typeof value.strength === "number" && value.strength >= 0 && value.strength <= 100
    && value.range === "1M" && ["Positive", "Balanced", "Cautious"].includes(String(value.rating))
    && value.classification_label === "simulated classification";
}
function isDiscoveryData(value: unknown): value is DiscoveryData {
  return isRecord(value) && Array.isArray(value.sectors) && value.sectors.every((v) => typeof v === "string")
    && Array.isArray(value.industries) && value.industries.every((row) => isRecord(row) && typeof row.name === "string" && typeof row.sector === "string" && typeof row.company_count === "number")
    && Array.isArray(value.companies) && value.companies.every(isDiscoveryCompany)
    && (value.selected_sector === null || typeof value.selected_sector === "string")
    && (value.selected_industry === null || typeof value.selected_industry === "string")
    && typeof value.query === "string" && typeof value.disclosure === "string";
}

async function requestData<T>(path: string, signal: AbortSignal | undefined, validate: (value: unknown) => value is T, timeoutMs = requestTimeoutMs): Promise<ApiEnvelope<T>> {
  const timeout = new AbortController();
  const timeoutId = window.setTimeout(() => timeout.abort(), timeoutMs);
  const forwardAbort = () => timeout.abort();
  signal?.addEventListener("abort", forwardAbort, { once: true });
  try {
    if (!baseUrl) {
      throw new ApiRequestError("Company Research is unavailable because the API address is not configured for this release.", "unavailable", 503);
    }
    const response = await fetch(`${baseUrl}${path}`, { method: "GET", headers: { Accept: "application/json" }, signal: timeout.signal });
    let payload: unknown;
    try { payload = await response.json(); } catch { throw new ApiRequestError("The local API returned an unreadable response.", "failed", response.status); }
    if (!isEnvelope(payload)) throw new ApiRequestError("The local API response did not match the expected contract.", "failed", response.status);
    if (!response.ok || payload.data === null) {
      const status = payload.status === "invalid" || payload.status === "unavailable" || payload.status === "rate_limited" ? payload.status : "failed";
      throw new ApiRequestError(payload.warnings[0] ?? "The local API request could not be completed.", status, response.status);
    }
    if (!validate(payload.data)) throw new ApiRequestError("The local API data did not match the expected response shape.", "failed", response.status);
    return payload as ApiEnvelope<T>;
  } catch (error) {
    if (error instanceof ApiRequestError) throw error;
    if (timeout.signal.aborted) {
      if (signal?.aborted) throw new DOMException("The request was cancelled.", "AbortError");
      throw new ApiRequestError(import.meta.env.DEV
        ? "The local API timed out. Confirm that the demo service is running."
        : "The application API timed out. Try again later.", "failed");
    }
    throw new ApiRequestError(import.meta.env.DEV
      ? "The local API could not be reached. Confirm that it is running on localhost."
      : "The application API could not be reached. Try again later.", "failed");
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", forwardAbort);
  }
}

function isTickerSearchData(value: unknown): value is TickerSearchData {
  return isRecord(value) && typeof value.query === "string" && Array.isArray(value.results)
    && value.results.every((row) => isRecord(row) && ["symbol", "name", "exchange", "sector", "industry"].every((key) => typeof row[key] === "string"));
}
function isChartData(value: unknown): value is ChartData {
  return isRecord(value) && typeof value.symbol === "string" && ["1D", "1W", "1M", "3M", "1Y", "ALL"].includes(String(value.range)) && chartResolutions.includes(value.interval as ChartResolution)
    && typeof value.label === "string" && Array.isArray(value.bars)
    && value.bars.every((bar) => isRecord(bar) && typeof bar.time === "string" && ["open", "high", "low", "close", "volume"].every((key) => typeof bar[key] === "number" && Number.isFinite(bar[key])));
}
function isCalendarData(value: unknown): value is DiscoveryCalendarData {
  return isRecord(value) && (value.kind === "earnings" || value.kind === "ipos") && typeof value.window_days === "number"
    && Array.isArray(value.items) && value.items.every((row) => isRecord(row) && ["symbol", "name", "date_label", "title", "detail"].every((key) => typeof row[key] === "string"))
    && typeof value.disclosure === "string";
}
function isWatchlistSummaryData(value: unknown): value is WatchlistSummaryData {
  return isRecord(value) && Array.isArray(value.symbols) && Array.isArray(value.summaries)
    && value.summaries.every((row) => isRecord(row) && ["symbol", "name", "sector", "industry", "technical_rating", "trend_state"].every((key) => typeof row[key] === "string")
      && (row.sample_close === null || typeof row.sample_close === "number")
      && (row.sample_change_percent === null || typeof row.sample_change_percent === "number"))
    && typeof value.disclosure === "string";
}
function isTechnicalData(value: unknown): value is TechnicalAnalysisData {
  return isRecord(value) && typeof value.symbol === "string" && typeof value.name === "string" && isRecord(value.indicators)
    && Object.values(value.indicators).every((v) => v === null || (typeof v === "number" && Number.isFinite(v)))
    && typeof value.rating === "string" && typeof value.rating_source === "string" && typeof value.technical_rating === "string"
    && Array.isArray(value.rating_checks) && value.rating_checks.every((check) => isRecord(check) && typeof check.label === "string")
    && isRecord(value.returns) && typeof value.observations === "number" && typeof value.disclosure === "string";
}
function isResearchData(value: unknown): value is ResearchData {
  return isRecord(value) && typeof value.symbol === "string" && typeof value.name === "string" && Array.isArray(value.fundamentals)
    && value.fundamentals.every((row) => isRecord(row) && typeof row.label === "string" && typeof row.display_value === "string")
    && Array.isArray(value.quarterly_financials) && isRecord(value.analyst_consensus) && Array.isArray(value.recommendation_distribution)
    && Array.isArray(value.eps_revisions) && Array.isArray(value.events) && typeof value.disclosure === "string";
}
function isNewsEventsData(value: unknown): value is NewsEventsData {
  return isRecord(value) && typeof value.symbol === "string" && Array.isArray(value.headlines)
    && value.headlines.every((row) => isRecord(row) && typeof row.title === "string" && ["Bullish", "Bearish", "Neutral"].includes(String(row.sentiment)) && typeof row.issuer_relevant === "boolean")
    && Array.isArray(value.events) && typeof value.disclosure === "string";
}
function isSecCompanyReport(value: unknown): value is SecCompanyReport {
  const factKeys = ["field", "taxonomy", "tag", "label", "original_value", "unit", "period_end", "form", "filed", "accession_number"];
  if (!isRecord(value) || !isRecord(value.identity)) return false;
  const identity = value.identity;
  return ["cik", "ticker", "name"].every((key) => typeof identity[key] === "string")
    && identity.identity_source === "sec_company_tickers"
    && (identity.exchange === null || typeof identity.exchange === "string")
    && Array.isArray(value.facts) && value.facts.every((fact) => isRecord(fact) && factKeys.every((key) => typeof fact[key] === "string")
      && typeof fact.value === "number" && Number.isFinite(fact.value) && typeof fact.latest_reported_version === "boolean"
      && (fact.filing_url === null || typeof fact.filing_url === "string"))
    && Array.isArray(value.filings) && value.filings.every((filing) => isRecord(filing) && ["cik", "accession_number", "form", "filing_date"].every((key) => typeof filing[key] === "string"))
    && ["annual_periods", "quarterly_periods", "ytd_periods"].every((key) => value[key] === undefined || (Array.isArray(value[key]) && value[key].every(isSecStatementPeriod)))
    && Array.isArray(value.missing_fields) && value.missing_fields.every((field) => typeof field === "string")
    && (value.status === "ok" || value.status === "partial") && value.live_data === true
    && Array.isArray(value.warnings) && value.warnings.every((warning) => typeof warning === "string");
}
function isSecStatementPeriod(value: unknown): value is SecStatementPeriod {
  if (!isRecord(value) || !["annual", "quarterly", "ytd"].includes(String(value.period_type))
      || typeof value.period_end !== "string" || !isRecord(value.metrics)
      || !(value.fiscal_year === null || typeof value.fiscal_year === "number")
      || !(value.fiscal_period === null || typeof value.fiscal_period === "string")
      || !(value.period_start === null || typeof value.period_start === "string")) return false;
  return Object.entries(value.metrics).every(([field, metricRows]) => typeof field === "string" && Array.isArray(metricRows)
    && metricRows.every((metric) => isRecord(metric) && typeof metric.field === "string"
      && typeof metric.taxonomy === "string" && typeof metric.label === "string"
      && typeof metric.value === "number" && Number.isFinite(metric.value)
      && typeof metric.original_value === "string" && typeof metric.unit === "string"
      && (metric.currency === null || typeof metric.currency === "string")
      && (metric.period_start === null || typeof metric.period_start === "string")
      && (metric.duration_days === null || typeof metric.duration_days === "number")
      && typeof metric.tag === "string" && typeof metric.form === "string"
      && typeof metric.filed === "string" && typeof metric.accession_number === "string"
      && typeof metric.period_end === "string" && (metric.filing_url === null || typeof metric.filing_url === "string")
      && (metric.comparison_percent === null || (typeof metric.comparison_percent === "number" && Number.isFinite(metric.comparison_percent)))
      && (metric.comparison_period_end === null || typeof metric.comparison_period_end === "string")
      && (metric.comparison_value === undefined || metric.comparison_value === null || typeof metric.comparison_value === "string")
      && (metric.comparison_filed === undefined || metric.comparison_filed === null || typeof metric.comparison_filed === "string")
      && (metric.comparison_form === undefined || metric.comparison_form === null || typeof metric.comparison_form === "string")
      && (metric.comparison_accession_number === undefined || metric.comparison_accession_number === null || typeof metric.comparison_accession_number === "string")
      && (metric.comparison_filing_url === undefined || metric.comparison_filing_url === null || typeof metric.comparison_filing_url === "string")));
}
function isSecDirectoryData(value: unknown): value is SecDirectoryData {
  return isRecord(value) && Array.isArray(value.companies)
    && value.companies.every((company) => isRecord(company) && typeof company.ticker === "string"
      && typeof company.name === "string" && typeof company.cik === "string"
      && (company.exchange === null || typeof company.exchange === "string"))
    && typeof value.total === "number" && Number.isInteger(value.total) && value.total >= 0
    && typeof value.limit === "number" && Number.isInteger(value.limit) && value.limit >= 1 && value.limit <= 50
    && typeof value.offset === "number" && Number.isInteger(value.offset) && value.offset >= 0
    && typeof value.query === "string" && (value.exchange === null || typeof value.exchange === "string")
    && Array.isArray(value.available_exchanges) && value.available_exchanges.every((item) => typeof item === "string")
    && typeof value.disclosure === "string";
}
function isSecFilingsData(value: unknown): value is SecFilingsData {
  return isRecord(value) && ["ticker", "company_name", "cik"].every((key) => typeof value[key] === "string")
    && ["exchange", "sic", "sic_description"].every((key) => value[key] === null || typeof value[key] === "string")
    && Array.isArray(value.forms) && value.forms.every((form) => typeof form === "string")
    && Array.isArray(value.filings) && value.filings.every((filing) => isRecord(filing)
      && ["cik", "ticker", "company_name", "form", "filing_date", "accession_number"].every((key) => typeof filing[key] === "string")
      && ["exchange", "sic", "sic_description", "report_date", "primary_document", "filing_url"].every((key) => filing[key] === null || typeof filing[key] === "string")
      && (filing.items === undefined || filing.items === null || typeof filing.items === "string"))
    && typeof value.disclosure === "string";
}

export function fetchOverview(signal?: AbortSignal) {
  return requestData("/overview", signal, isOverviewData);
}

export function fetchTickerSearch(query: string, signal?: AbortSignal) {
  return requestData(`/tickers/search?q=${encodeURIComponent(query)}`, signal, isTickerSearchData);
}
export function fetchChart(symbol: string, range: ChartRange, interval: ChartResolution = "1d", signal?: AbortSignal) {
  return requestData(`/tickers/${encodeURIComponent(symbol)}/chart?range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}`, signal, isChartData);
}
export function fetchTechnicalAnalysis(symbol: string, signal?: AbortSignal) {
  return requestData(`/tickers/${encodeURIComponent(symbol)}/analysis`, signal, isTechnicalData);
}
export function fetchCompanyResearch(symbol: string, signal?: AbortSignal) {
  return requestData(`/companies/${encodeURIComponent(symbol)}/research`, signal, isResearchData);
}
export function fetchNewsEvents(symbol: string, signal?: AbortSignal) {
  return requestData(`/companies/${encodeURIComponent(symbol)}/news-events`, signal, isNewsEventsData);
}
export function fetchSecResearch(symbol: string, signal?: AbortSignal, exchange?: string | null) {
  const params = new URLSearchParams();
  if (exchange) params.set("exchange", exchange);
  const suffix = params.size ? `?${params.toString()}` : "";
  return requestData(`/companies/${encodeURIComponent(symbol)}/sec-research${suffix}`, signal, isSecCompanyReport, secRequestTimeoutMs);
}

export function fetchSecDirectory(filters: { query?: string; exchange?: string; limit?: number; offset?: number }, signal?: AbortSignal) {
  const params = new URLSearchParams();
  if (filters.query) params.set("q", filters.query);
  if (filters.exchange) params.set("exchange", filters.exchange);
  params.set("limit", String(filters.limit ?? 25));
  params.set("offset", String(filters.offset ?? 0));
  return requestData(`/discovery/companies?${params.toString()}`, signal, isSecDirectoryData, secRequestTimeoutMs);
}

export function fetchSecFilings(symbol: string, exchange?: string, signal?: AbortSignal) {
  const params = new URLSearchParams();
  if (exchange) params.set("exchange", exchange);
  const suffix = params.size ? `?${params.toString()}` : "";
  return requestData(`/discovery/filings/${encodeURIComponent(symbol)}${suffix}`, signal, isSecFilingsData, secRequestTimeoutMs);
}

export function fetchDiscovery(filters: { sector?: string; industry?: string; query?: string }, signal?: AbortSignal) {
  const params = new URLSearchParams();
  if (filters.sector && filters.sector !== "All sectors") params.set("sector", filters.sector);
  if (filters.industry && filters.industry !== "All industries") params.set("industry", filters.industry);
  if (filters.query) params.set("q", filters.query);
  const suffix = params.size ? `?${params.toString()}` : "";
  return requestData(`/discovery${suffix}`, signal, isDiscoveryData);
}

export function fetchDiscoveryCalendar(kind: "earnings" | "ipos", windowDays = 60, signal?: AbortSignal) {
  return requestData(`/discovery/calendar?kind=${kind}&window_days=${windowDays}`, signal, isCalendarData);
}

export function fetchWatchlistSummaries(symbols: string[], signal?: AbortSignal) {
  const query = encodeURIComponent(symbols.join(","));
  return requestData(`/watchlist/summaries?symbols=${query}`, signal, isWatchlistSummaryData);
}

