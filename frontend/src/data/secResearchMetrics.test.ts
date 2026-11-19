import { describe, expect, it } from "vitest";
import type { SecCompanyReport, SecStatementMetric, SecStatementPeriod } from "./apiClient";
import { buildSecResearchMetrics, reportableBalanceSheetContext } from "./secResearchMetrics";

function value(overrides: Partial<SecStatementMetric> = {}): SecStatementMetric {
  return {
    field: "revenue",
    taxonomy: "us-gaap",
    tag: "Revenues",
    label: "Revenue",
    value: 0,
    original_value: "100",
    unit: "USD",
    currency: "USD",
    period_start: "2025-01-01",
    period_end: "2025-12-31",
    duration_days: 365,
    form: "10-K",
    filed: "2026-02-01",
    accession_number: "current-accession",
    filing_url: "https://www.sec.gov/Archives/edgar/data/1/current/report.htm",
    comparison_percent: null,
    comparison_period_end: null,
    ...overrides,
  };
}

function period(
  fiscalYear: number,
  fiscalPeriod: string,
  periodType: SecStatementPeriod["period_type"],
  start: string | null,
  end: string,
  metrics: Record<string, SecStatementMetric[]>,
): SecStatementPeriod {
  return {
    fiscal_year: fiscalYear,
    fiscal_period: fiscalPeriod,
    period_type: periodType,
    period_start: start,
    period_end: end,
    metrics,
  };
}

function report(
  annualPeriods: SecStatementPeriod[],
  quarterlyPeriods: SecStatementPeriod[] = [],
  ytdPeriods: SecStatementPeriod[] = [],
): SecCompanyReport {
  return {
    identity: { cik: "0000000001", ticker: "TEST", name: "Test Corp.", exchange: "NYSE", identity_source: "sec_company_tickers" },
    facts: [],
    annual_periods: annualPeriods,
    quarterly_periods: quarterlyPeriods,
    ytd_periods: ytdPeriods,
    filings: [],
    missing_fields: [],
    source: "sec-edgar",
    live_data: true,
    status: "ok",
    as_of: null,
    warnings: [],
  };
}

describe("SEC-derived research metrics", () => {
  it("derives same-period margins, comparable annual growth and free cash flow with source provenance", () => {
    const prior = period(2024, "FY", "annual", "2024-01-01", "2024-12-31", {
      revenue: [value({ original_value: "80", period_start: "2024-01-01", period_end: "2024-12-31", duration_days: 366, accession_number: "prior-accession" })],
    });
    const current = period(2025, "FY", "annual", "2025-01-01", "2025-12-31", {
      revenue: [value()],
      operating_income: [value({ field: "operating_income", label: "Operating income", original_value: "20" })],
      net_income: [value({ field: "net_income", label: "Net income", original_value: "10" })],
      operating_cash_flow: [value({ field: "operating_cash_flow", label: "Operating cash flow", original_value: "25" })],
      capital_expenditures: [value({ field: "capital_expenditures", label: "Capital expenditures", original_value: "-5" })],
      cash_and_equivalents: [value({ field: "cash_and_equivalents", label: "Cash and cash equivalents", original_value: "15", period_start: null, duration_days: null })],
      long_term_debt_current: [value({ field: "long_term_debt_current", label: "Current long-term debt", original_value: "9", period_start: null, duration_days: null })],
      long_term_debt_noncurrent: [value({ field: "long_term_debt_noncurrent", label: "Noncurrent long-term debt", original_value: "11", period_start: null, duration_days: null })],
    });

    const metrics = buildSecResearchMetrics(report([current, prior]));
    const byLabel = new Map(metrics.map((item) => [item.label, item]));
    expect(byLabel.get("Revenue year-over-year")?.value).toBe("25%");
    expect(byLabel.get("Operating profit margin")?.value).toBe("20%");
    expect(byLabel.get("Net profit margin")?.value).toBe("10%");
    expect(byLabel.get("Free cash flow")?.value).toBe("$20 USD");
    expect(byLabel.get("Revenue year-over-year")?.sources.map((row) => row.accession_number)).toEqual(["current-accession", "prior-accession"]);
    expect(byLabel.get("Operating profit margin")?.formula).toContain("20 USD ÷ 100 USD");

    expect(reportableBalanceSheetContext(report([current, prior]))).toEqual([
      ["Cash and cash equivalents", current.metrics.cash_and_equivalents![0]],
      ["Current long-term debt", current.metrics.long_term_debt_current![0]],
      ["Noncurrent long-term debt", current.metrics.long_term_debt_noncurrent![0]],
    ]);
  });

  it("does not bridge annual, quarterly, and cumulative YTD windows", () => {
    const currentAnnual = period(2025, "FY", "annual", "2025-01-01", "2025-12-31", {
      revenue: [value()],
    });
    const priorYtd = period(2024, "FY", "ytd", "2024-01-01", "2024-09-30", {
      revenue: [value({ original_value: "80", period_start: "2024-01-01", period_end: "2024-09-30", duration_days: 274 })],
    });
    const result = buildSecResearchMetrics(report([currentAnnual], [], [priorYtd]));
    expect(result.some((item) => item.label === "Revenue year-over-year")).toBe(false);
  });

  it("abstains on conflicting, cross-period, or non-finite source values", () => {
    const conflicting = period(2025, "FY", "annual", "2025-01-01", "2025-12-31", {
      revenue: [value({ original_value: "100" }), value({ original_value: "101", accession_number: "other-accession" })],
      operating_income: [value({ field: "operating_income", original_value: "20" })],
    });
    expect(buildSecResearchMetrics(report([conflicting]))).toEqual([]);

    const mismatched = period(2025, "FY", "annual", "2025-01-01", "2025-12-31", {
      revenue: [value()],
      operating_income: [value({ field: "operating_income", original_value: "20", period_start: "2025-02-01" })],
    });
    expect(buildSecResearchMetrics(report([mismatched])).some((item) => item.label === "Operating profit margin")).toBe(false);

    const nonFinite = period(2025, "FY", "annual", "2025-01-01", "2025-12-31", {
      revenue: [value({ original_value: "NaN" })],
      operating_income: [value({ field: "operating_income", original_value: "20" })],
    });
    expect(buildSecResearchMetrics(report([nonFinite]))).toEqual([]);
  });
});
