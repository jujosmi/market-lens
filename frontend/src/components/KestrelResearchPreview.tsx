import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, ShieldAlert } from "lucide-react";
import { ApiRequestError, fetchKestrelResearchPreview, type KestrelResearchPreview } from "../data/apiClient";

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Unavailable";
  if (typeof value === "string") return value.replaceAll("_", " ");
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "object" && value !== null && "status" in value) return display((value as Record<string, unknown>).status);
  return "Unavailable";
}

export function KestrelResearchPreview() {
  const [preview, setPreview] = useState<KestrelResearchPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchKestrelResearchPreview(controller.signal)
      .then(setPreview)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setPreview(null);
        setError(reason instanceof ApiRequestError ? reason.message : "The local preview is unavailable.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [retry]);

  const record = preview?.bundle.record;
  const response = record?.research_response;
  const research = response?.research_record;
  const daily = research?.daily_context;
  const intraday = research?.intraday_context;
  const provenance = record?.source_provenance;

  return <section className="kestrel-preview" aria-labelledby="kestrel-preview-title">
    <header className="kestrel-preview-header">
      <div><span className="section-kicker">LOCAL DEVELOPMENT ONLY · SYNTHETIC</span><h2 id="kestrel-preview-title">Kestrel Research — Development Preview</h2></div>
      <span className="kestrel-preview-badge">{preview?.stale ? "HISTORICAL · STALE" : "HISTORICAL SYNTHETIC"}</span>
    </header>
    <div className="kestrel-preview-warning" role="note"><ShieldAlert size={16} /><span>Synthetic research example. Not current market data, a forecast, live signal, or recommendation.</span></div>
    {loading && <p className="kestrel-preview-state" role="status">Loading the local Kestrel research record…</p>}
    {error && <div className="kestrel-preview-state kestrel-preview-error" role="alert"><AlertTriangle size={16} /><span>{error}</span><button className="quiet-button" onClick={() => setRetry((value) => value + 1)}><RefreshCw size={13} /> Retry</button></div>}
    {record && research && <div className="kestrel-preview-content">
      <div className="kestrel-preview-summary">
        <div><span>Instrument</span><strong>{record.instrument.symbol}</strong></div>
        <div><span>Observation time</span><strong>{record.observation_timing.observation_timestamp_utc}</strong></div>
        <div><span>Descriptive classification</span><strong>{display(research.unified_descriptive_classification)}</strong></div>
        <div><span>Completeness</span><strong>{display(research.completeness_status)} · {display(response?.outcome)}</strong></div>
      </div>
      <div className="kestrel-preview-contexts">
        <article><span className="section-kicker">DAILY CONTEXT</span>
          <p>Trend: <b>{display(daily?.trend_classification)}</b></p>
          <p>Momentum: <b>{display(daily?.momentum_classification)}</b></p>
          <p>Volatility: <b>{display(daily?.volatility_classification)}</b></p>
          <p>Volume confirmation: <b>{display(daily?.volume_confirmation)}</b></p>
        </article>
        <article><span className="section-kicker">INTRADAY CONTEXT</span>
          <p>1-minute trend: <b>{display(intraday?.trend_1m)}</b></p>
          <p>5-minute trend: <b>{display(intraday?.trend_5m)}</b></p>
          <p>Price vs. VWAP: <b>{display(intraday?.price_vs_vwap)}</b></p>
          <p>Data quality: <b>{display(intraday?.data_quality_status)}</b></p>
        </article>
      </div>
      <div className="kestrel-preview-details">
        <div><span>Source</span><b>{display(provenance?.daily?.source_provider)} / {display(provenance?.intraday?.source_provider)}</b></div>
        <div><span>Scenario</span><b>{record.scenario_id.replaceAll("_", " ")}</b></div>
        <div><span>Schema</span><b>{record.bridge_contract_id} · v{record.schema_version}</b></div>
        <div><span>Manifest digest</span><code>{preview?.bundle.manifest.manifest_sha256.slice(0, 16)}…</code></div>
      </div>
      {preview?.stale && <p className="kestrel-preview-stale" role="status">This record is historical and stale. It is shown only to demonstrate the offline transfer.</p>}
      {(research.data_quality_flags.length > 0 || research.abstention_reasons.length > 0 || record.m913_quality_notes.length > 0) && <details className="kestrel-preview-limitations">
        <summary>Data quality and abstentions</summary>
        {[...record.m913_quality_notes, ...research.data_quality_flags, ...research.abstention_reasons].map((item, index) => <span key={item + "-" + index}>{item.replaceAll("_", " ")}</span>)}
      </details>}
      <footer>Private local preview · rights unverified · public and commercial display disabled</footer>
    </div>}
  </section>;
}