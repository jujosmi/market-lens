import { useState } from "react";
import type { SecCompanyReport, SecStatementMetric, SecStatementPeriod } from "../data/apiClient";

const metricDefinitions: { field: string; title: string }[] = [
  { field: "revenue", title: "Revenue" },
  { field: "operating_income", title: "Operating income" },
  { field: "net_income", title: "Net income" },
  { field: "diluted_eps", title: "Diluted EPS" },
  { field: "operating_cash_flow", title: "Operating cash flow" },
  { field: "capital_expenditures", title: "Capital expenditures" },
  { field: "assets", title: "Total assets" },
  { field: "liabilities", title: "Total liabilities" },
  { field: "stockholders_equity", title: "Stockholders’ equity" },
  { field: "cash_and_equivalents", title: "Cash and cash equivalents" },
  { field: "long_term_debt_current", title: "Current long-term debt" },
  { field: "long_term_debt_noncurrent", title: "Noncurrent long-term debt" },
];

function periodTitle(period: SecStatementPeriod) {
  if (period.period_type === "annual") return `FY ${period.fiscal_year ?? "unavailable"}`;
  return `${period.fiscal_period ?? "Fiscal period unavailable"} FY${period.fiscal_year ?? ""}`;
}

function provenance(metric: SecStatementMetric) {
  return <details className="sec-statement-provenance">
    <summary>SEC source</summary>
    <dl>
      <dt>Reported concept</dt><dd>{metric.taxonomy} · {metric.tag} · {metric.label}</dd>
      <dt>Period</dt><dd>{metric.period_start ? `${metric.period_start} through ` : "As of "}{metric.period_end}{metric.duration_days ? ` · ${metric.duration_days} days` : " · instant balance"}</dd>
      <dt>Filing</dt><dd>{metric.form} · filed {metric.filed}</dd>
      <dt>Accession</dt><dd>{metric.accession_number}</dd>
      {metric.filing_url && <dt>Original document</dt>}
      {metric.filing_url && <dd><a href={metric.filing_url} target="_blank" rel="noreferrer">Open SEC filing document</a></dd>}
    </dl>
  </details>;
}

function MetricRows({ period }: { period: SecStatementPeriod }) {
  const definitions = period.period_type === "ytd"
    ? metricDefinitions.filter(({ field }) => !["assets", "liabilities", "stockholders_equity", "cash_and_equivalents", "long_term_debt_current", "long_term_debt_noncurrent"].includes(field))
    : metricDefinitions;
  return <div className="sec-statement-metrics">
    {definitions.map(({ field, title }) => {
      const values = period.metrics[field] ?? [];
      return <article className="sec-statement-metric" key={field}>
        <div className="sec-statement-metric-heading"><b>{title}</b><span>{values.length ? "Reported value" : "Unavailable for this period"}</span></div>
        {values.length ? values.map((metric, index) => <div className="sec-statement-value" key={`${metric.unit}-${metric.accession_number}-${index}`}>
          <div className="sec-statement-amount"><strong>{metric.original_value}</strong><span>{metric.unit}</span></div>
          <div className="sec-statement-change" aria-label={metric.comparison_percent === null ? "Year-over-year comparison unavailable" : `Year-over-year change ${metric.comparison_percent.toFixed(2)} percent`}>
            {metric.comparison_percent === null ? <span>YoY unavailable</span> : <span className={metric.comparison_percent >= 0 ? "sec-change-positive" : "sec-change-negative"}>{metric.comparison_percent >= 0 ? "+" : ""}{metric.comparison_percent.toFixed(2)}% YoY</span>}
            {metric.comparison_period_end && <small>vs. {metric.comparison_period_end}</small>}
          </div>
          {provenance(metric)}
        </div>) : <p className="sec-statement-unavailable">The SEC response contains no mapped value for this measure in this period. It is not treated as zero.</p>}
      </article>;
    })}
  </div>;
}

function PeriodList({ periods, emptyLabel, report }: { periods: SecStatementPeriod[]; emptyLabel: string; report: SecCompanyReport }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? periods : periods.slice(0, 12);
  if (!periods.length) return <div className="sec-statement-empty" role="status"><b>{emptyLabel}</b><p>No eligible SEC periods were returned for the supported standard concepts. No missing values have been filled or derived.</p></div>;
  return <>
    <div className="sec-statement-period-list">
      {visible.map((period, index) => <section className="sec-statement-period" key={`${period.period_type}-${period.fiscal_year}-${period.fiscal_period}-${period.period_end}`}>
        <header><div><span className="section-kicker">{index === 0 ? `LATEST REPORTED ${period.period_type === "annual" ? "FISCAL YEAR" : "FISCAL QUARTER"}` : period.period_type.toUpperCase() + " DISCLOSURE"}</span><h3>{periodTitle(period)}</h3></div><span className="sec-period-end">Period end · {period.period_end}</span></header>
        <MetricRows period={period} />
      </section>)}
    </div>
    {periods.length > 12 && <button className="quiet-button sec-period-expand" onClick={() => setShowAll((value) => !value)}>{showAll ? "Show fewer periods" : `Show all ${periods.length} periods`}</button>}
    {report.missing_fields.length > 0 && <p className="table-caption">Not present in the supported standard taxonomy: {report.missing_fields.join(", ")}.</p>}
  </>;
}

export function SecFinancialStatements({ report }: { report: SecCompanyReport }) {
  const [view, setView] = useState<"annual" | "quarterly">("annual");
  const annual = report.annual_periods ?? [];
  const quarterly = report.quarterly_periods ?? [];
  const ytd = report.ytd_periods ?? [];
  return <section className="sec-financial-statements" aria-label="SEC financial statements">
    <div className="sec-statement-heading"><div><span className="section-kicker">SEC COMPANY FACTS · AS REPORTED</span><h3>Financial statements</h3><p>Reported values retain their SEC units and original number strings. Comparisons use matching metric, unit, fiscal period, and comparable report duration.</p></div>
      <div className="sec-statement-toggle" role="group" aria-label="Financial statement period"><button type="button" aria-pressed={view === "annual"} onClick={() => setView("annual")}>Annual</button><button type="button" aria-pressed={view === "quarterly"} onClick={() => setView("quarterly")}>Quarterly</button></div>
    </div>
    {view === "annual" ? <PeriodList periods={annual} emptyLabel="Annual data unavailable" report={report} /> : <>
      <PeriodList periods={quarterly} emptyLabel="Standalone quarterly data unavailable" report={report} />
      <section className="sec-ytd-section"><header><span className="section-kicker">CUMULATIVE PERIODS</span><h3>Year-to-date disclosures</h3><p>Six- and nine-month values are cumulative filing amounts, kept separate from standalone quarters. No subtraction is used to create quarter values.</p></header><PeriodList periods={ytd} emptyLabel="Year-to-date data unavailable" report={report} /></section>
    </>}
  </section>;
}
