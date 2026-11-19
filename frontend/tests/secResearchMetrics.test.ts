import { describe, expect, it } from "vitest";
import type { SecCompanyReport, SecStatementMetric, SecStatementPeriod } from "../src/data/apiClient";
import { buildSecResearchMetrics, reportableBalanceSheetContext } from "../src/data/secResearchMetrics";

function metric(field: string, value: string, unit: string, start: string | null, end: string, accession: string, duration: number | null = 365): SecStatementMetric {
  return { field, taxonomy: "us-gaap", tag: field, label: field, value: Number(value), original_value: value, unit,
    currency: unit === "USD" ? "USD" : null, period_start: start, period_end: end, duration_days: duration,
    form: "10-K", filed: `${end.slice(0, 4)}-02-01`, accession_number: accession,
    filing_url: `https://www.sec.gov/Archives/${accession}`, comparison_percent: null, comparison_period_end: null };
}

function annual(year: number, values: Record<string, string>, accession: string): SecStatementPeriod {
  const end = `${year}-12-31`; const start = `${year}-01-01`;
  return { fiscal_year: year, fiscal_period: "FY", period_type: "annual", period_start: start, period_end: end,
    metrics: Object.fromEntries(Object.entries(values).map(([field, value]) => [field, [metric(field, value, field === "diluted_eps" ? "USD/shares" : "USD", start, end, accession)]])) };
}

function report(periods: SecStatementPeriod[]): SecCompanyReport {
  return { identity: { cik: "0000000001", ticker: "EXMP", name: "Example Inc", exchange: "Nasdaq", identity_source: "sec_company_tickers" },
    facts: [], annual_periods: periods, quarterly_periods: [], ytd_periods: [], filings: [], missing_fields: [],
    source: "SEC EDGAR", live_data: true, status: "ok", as_of: "2026-11-18T00:00:00Z", warnings: [] };
}

describe("SEC derived research metrics", () => {
  it("calculates period-matched growth, margins, and free cash flow with source records", () => {
    const result = buildSecResearchMetrics(report([
      annual(2025, { revenue: "120", operating_income: "24", net_income: "12", operating_cash_flow: "30", capital_expenditures: "8" }, "fy25"),
      annual(2024, { revenue: "100", operating_income: "18", net_income: "9", operating_cash_flow: "25", capital_expenditures: "5" }, "fy24"),
    ]));
    expect(result.find((item) => item.key === "revenue-growth-annual-2025-12-31")).toMatchObject({ value: "20%", sources: expect.arrayContaining([expect.objectContaining({ accession_number: "fy25" }), expect.objectContaining({ accession_number: "fy24" })]) });
    expect(result.find((item) => item.key === "operating_margin-annual-2025-12-31")?.value).toBe("20%");
    expect(result.find((item) => item.key === "net_margin-annual-2025-12-31")?.value).toBe("10%");
    expect(result.find((item) => item.key === "free-cash-flow-annual-2025-12-31")?.value).toBe("$22 USD");
  });

  it("omits zero-base growth and mismatched-unit margins while retaining valid same-period metrics", () => {
    const current = annual(2025, { revenue: "100", operating_income: "20", net_income: "1" }, "fy25");
    const prior = annual(2024, { revenue: "0" }, "fy24");
    current.metrics.operating_income = [metric("operating_income", "20", "EUR", "2025-01-01", "2025-12-31", "eur")];
    const result = buildSecResearchMetrics(report([current, prior]));
    expect(result.map((item) => item.key)).toEqual(["net_margin-annual-2025-12-31"]);
  });

  it("shows only reported debt and cash balances with their SEC provenance", () => {
    const period = annual(2025, { cash_and_equivalents: "500", long_term_debt_current: "40", long_term_debt_noncurrent: "200" }, "fy25");
    const rows = reportableBalanceSheetContext(report([period]));
    expect(rows.map(([label]) => label)).toEqual(["Cash and cash equivalents", "Current long-term debt", "Noncurrent long-term debt"]);
    expect(rows[0]?.[1].accession_number).toBe("fy25");
  });
});
