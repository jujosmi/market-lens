import { useEffect, useState } from "react";
import { ArrowDownRight, Clock3, FileText, RefreshCw } from "lucide-react";
import { ApiRequestError, fetchSecWatchlistActivity, type SecFilingActivity } from "../data/apiClient";
import { accessionsNewSinceReview, markSuccessfulFilingsReviewed, readSecFilingReviewSnapshot, writeSecFilingReviewSnapshot, type SecFilingReviewSnapshot } from "../data/secFilingReview";

export type WatchlistActivityCompany = { ticker: string; exchange: string | null };
type ResearchNavigation = (workspace: "research" | "overview") => void;

const COMPANY_LIMIT = 5;
const SUPPORTED_FORM_FILTERS = ["All forms", "10-K", "10-Q", "8-K"] as const;
type FilingFilter = (typeof SUPPORTED_FORM_FILTERS)[number];

function normalizeCompanies(companies: readonly WatchlistActivityCompany[]) {
  const unique = new Map<string, WatchlistActivityCompany>();
  for (const company of companies) {
    const ticker = company.ticker.trim().toUpperCase();
    if (!ticker) continue;
    const exchange = company.exchange?.trim() || null;
    const key = ticker + "|" + (exchange ?? "");
    if (!unique.has(key)) unique.set(key, { ticker, exchange });
  }
  return Array.from(unique.values());
}

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function sortFilings(filings: readonly SecFilingActivity[]) {
  return [...filings].sort((left, right) => {
    const leftTime = left.acceptance_datetime ?? (left.filing_date + "T00:00:00Z");
    const rightTime = right.acceptance_datetime ?? (right.filing_date + "T00:00:00Z");
    return rightTime.localeCompare(leftTime)
      || right.filing_date.localeCompare(left.filing_date)
      || right.accession_number.localeCompare(left.accession_number);
  });
}

function matchesFilter(form: string, filter: FilingFilter) {
  return filter === "All forms" || form === filter || form === filter + "/A";
}

export function WatchlistFilingActivity({
  companies,
  reviewScope,
  onSelectTicker,
  onNavigate,
  disabled = false,
}: {
  companies: readonly WatchlistActivityCompany[];
  reviewScope: string;
  onSelectTicker: (symbol: string, exchange?: string) => void;
  onNavigate: ResearchNavigation;
  disabled?: boolean;
}) {
  const normalized = normalizeCompanies(companies);
  const requestCompanies = normalized.slice(0, COMPANY_LIMIT);
  const requestKey = JSON.stringify(requestCompanies);
  const [requestState, setRequestState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [response, setResponse] = useState<Awaited<ReturnType<typeof fetchSecWatchlistActivity>> | null>(null);
  const [requestError, setRequestError] = useState("");
  const [retry, setRetry] = useState(0);
  const [filter, setFilter] = useState<FilingFilter>("All forms");
  const [review, setReview] = useState<{ scope: string; value: SecFilingReviewSnapshot | null }>(() => ({
    scope: reviewScope,
    value: readSecFilingReviewSnapshot(reviewScope),
  }));
  const [storageWarning, setStorageWarning] = useState(false);
  const snapshot = review.scope === reviewScope ? review.value : readSecFilingReviewSnapshot(reviewScope);

  useEffect(() => {
    setReview({ scope: reviewScope, value: readSecFilingReviewSnapshot(reviewScope) });
  }, [reviewScope]);

  useEffect(() => {
    const requested = JSON.parse(requestKey) as WatchlistActivityCompany[];
    if (disabled || requested.length === 0) {
      setResponse(null);
      setRequestError("");
      setRequestState("idle");
      return;
    }
    const controller = new AbortController();
    let active = true;
    setRequestState("loading");
    setRequestError("");
    fetchSecWatchlistActivity(requested, controller.signal).then((result) => {
      if (!active) return;
      setResponse(result);
      setRequestState("ready");
    }).catch((error: unknown) => {
      if (!active || (error instanceof DOMException && error.name === "AbortError")) return;
      setRequestError(error instanceof ApiRequestError ? error.message : "SEC filing activity could not be checked.");
      setRequestState("error");
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [requestKey, retry, disabled]);

  function markReviewed() {
    const entries = response?.data?.entries ?? [];
    const next = markSuccessfulFilingsReviewed(snapshot, entries, new Date().toISOString());
    const stored = writeSecFilingReviewSnapshot(reviewScope, next);
    setReview({ scope: reviewScope, value: next });
    setStorageWarning(!stored);
  }

  const successfulEntries = response?.data?.entries.filter((entry) => entry.status === "ok" && entry.data) ?? [];
  const sourceDisclosures = Array.from(new Set((response?.data?.entries ?? []).map((entry) => entry.data?.disclosure).filter((value): value is string => Boolean(value?.trim()))));
  const sourceLabel = response?.provenance?.toLowerCase().includes("mock")
    ? "LOCAL ACCEPTANCE MOCK"
    : "OFFICIAL SEC EDGAR";

  return <section className="watchlist-filing-activity" aria-label="Watchlist Activity">
    <div className="watchlist-activity-heading">
      <div>
        <span className="section-kicker">SEC DISCLOSURE MONITORING</span>
        <h2>Watchlist Activity</h2>
        <p>Recent filings from SEC issuer submissions. New means an accession not present in your previous explicit review snapshot.</p>
      </div>
      <div className="watchlist-activity-controls">
        <span className="session-only-label"><Clock3 size={13} /> Session review only</span>
        <button type="button" className="quiet-button" onClick={() => setRetry((value) => value + 1)} disabled={requestState === "loading" || disabled || requestCompanies.length === 0}>
          <RefreshCw size={14} /> Refresh filings
        </button>
      </div>
    </div>
    {normalized.length > COMPANY_LIMIT && <p className="watchlist-activity-limit" role="status">SEC checks are bounded to the first {COMPANY_LIMIT} saved companies in this list.</p>}
    {disabled && <div className="workspace-state" role="status">Waiting for your saved account watchlist to finish loading.</div>}
    {!disabled && requestCompanies.length === 0 && <div className="table-empty">Save companies to see their recent SEC filings here.</div>}
    {requestState === "loading" && <div className="workspace-state" role="status">Checking recent SEC submissions for saved companies…</div>}
    {requestState === "error" && <div className="workspace-state workspace-error" role="alert"><span>{requestError || "SEC filing activity is unavailable."} Your saved watchlist remains available.</span><button type="button" className="quiet-button" onClick={() => setRetry((value) => value + 1)}>Retry SEC check</button></div>}
    {requestState === "ready" && response?.data && <>
      <div className="watchlist-activity-toolbar">
        <label className="filter-select"><span>Filing type</span><select aria-label="Filter filing type" value={filter} onChange={(event) => setFilter(event.target.value as FilingFilter)}>{SUPPORTED_FORM_FILTERS.map((item) => <option key={item}>{item}</option>)}</select></label>
        <button type="button" className="outline-button" onClick={markReviewed} disabled={successfulEntries.length === 0}>Mark successful companies reviewed</button>
      </div>
      {response.as_of && <p className="watchlist-activity-checked">Last successful check: {formatTimestamp(response.as_of)} · {sourceLabel}{response.freshness === "cached" ? " · cached SEC submissions" : ""}</p>}
      {response.warnings.map((warning) => <p className="table-caption" role="status" key={warning}>{warning}</p>)}
      {response.data.entries.map((entry) => {
        const data = entry.data;
        const previous = data ? snapshot?.issuers[data.cik] : undefined;
        const rows = data
          ? sortFilings(data.filings.filter((filing) => matchesFilter(filing.form, filter)))
          : [];
        const uniqueRows = Array.from(new Map(rows.map((filing) => [filing.accession_number, filing])).values());
        const fresh = data && entry.status === "ok" ? accessionsNewSinceReview(snapshot, data.cik, uniqueRows.map((filing) => filing.accession_number)) : null;
        return <article className="watchlist-activity-company" key={entry.requested_ticker + "|" + (entry.requested_exchange ?? "")}>
          <header className="watchlist-activity-company-heading">
            <div><h3>{data?.company_name ?? entry.requested_ticker} <small>{data?.ticker ?? entry.requested_ticker}</small></h3><p>{data ? "CIK " + data.cik + (data.exchange ? " · " + data.exchange : "") : "Exchange " + (entry.requested_exchange ?? "unavailable")}</p></div>
            {entry.status === "ok" && data
              ? previous
                ? <span className="activity-review-state">{fresh && fresh.size ? fresh.size + " new since review" : "No new accessions"}</span>
                : <span className="activity-review-state">Initial history · not yet reviewed</span>
              : <span className="activity-review-state activity-review-unavailable">{entry.status === "rate_limited" ? "SEC request limited" : entry.status === "partial" ? "Partial data · not reviewed" : "Activity unavailable"}</span>}
          </header>
          {entry.error && <p className="watchlist-activity-error" role="alert">{entry.error}</p>}
          {entry.warnings.map((warning) => <p className="table-caption" role="status" key={warning}>{warning}</p>)}
          {data && (entry.status === "ok" || entry.status === "partial") && <>
            {previous && entry.status === "ok" && <p className="watchlist-activity-reviewed">Last explicitly reviewed: {formatTimestamp(previous.reviewed_at)}</p>}
            <div className="watchlist-filing-list">
              {uniqueRows.map((filing) => {
                const isNew = fresh?.has(filing.accession_number) ?? false;
                const description = filing.primary_doc_description
                  || (filing.items ? "SEC filing items: " + filing.items : "Description unavailable in SEC submissions");
                const item202 = filing.items?.split(",").map((item) => item.trim()).includes("2.02") ?? false;
                return <div className="watchlist-filing-row" key={data.cik + ":" + filing.accession_number}>
                  <div className="watchlist-filing-main">
                    <div className="watchlist-filing-tags"><span className="rating-chip rating-balanced">{filing.form}</span>{isNew && previous && entry.status === "ok" && <span className="watchlist-new-tag">NEW SINCE REVIEW</span>}</div>
                    <h4>{data.company_name} <small>{data.ticker}</small></h4>
                    <p>Filed {filing.filing_date}{filing.acceptance_datetime ? " · accepted " + formatTimestamp(filing.acceptance_datetime) : " · acceptance time unavailable"}</p>
                    <p>{description}</p>
                    {item202 && <small className="watchlist-filing-item">SEC Item 2.02 is listed in the submission metadata; this is not a summary or earnings forecast.</small>}
                    <small className="watchlist-filing-accession">Accession {filing.accession_number}</small>
                  </div>
                  <div className="watchlist-filing-actions">
                    {filing.filing_url
                      ? <a className="row-research" href={filing.filing_url} target="_blank" rel="noopener noreferrer">View SEC filing <FileText size={13} /></a>
                      : <span className="unavailable-field">Official document link unavailable</span>}
                    <button type="button" className="row-research" onClick={() => { onSelectTicker(data.ticker, data.exchange ?? entry.requested_exchange ?? undefined); onNavigate("research"); }}>Company Research <ArrowDownRight size={13} /></button>
                  </div>
                </div>;
              })}
              {!uniqueRows.length && <div className="table-empty">No filings match this filter for {data.ticker}.</div>}
            </div>

          </>}
        </article>;
      })}
      {sourceDisclosures.map((disclosure) => <p className="watchlist-activity-disclosure" key={disclosure}>{disclosure}</p>)}
      {storageWarning && <p className="table-caption" role="status">The review is active in this view, but browser session storage was unavailable.</p>}
      <p className="table-caption">A filing’s presence does not imply a material change or investment signal. Activity is checked on demand and is not a permanent cross-device notification service.</p>
    </>}
  </section>;
}
