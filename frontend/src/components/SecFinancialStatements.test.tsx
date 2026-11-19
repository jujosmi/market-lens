import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SecFinancialStatements } from "./SecFinancialStatements";
import type { SecCompanyReport, SecStatementPeriod } from "../data/apiClient";

const value = {
  field: "revenue", taxonomy: "us-gaap", tag: "RevenueFromContractWithCustomerExcludingAssessedTax",
  label: "Revenue from contract with customer", value: 100, original_value: "100000000.25", unit: "USD",
  currency: "USD", period_start: "2025-01-01", period_end: "2025-12-31", duration_days: 365,
  form: "10-K", filed: "2026-02-15", accession_number: "0000000001-26-000001",
  filing_url: "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/annual.htm",
  comparison_percent: 25, comparison_period_end: "2024-12-31",
};
const annual: SecStatementPeriod = { fiscal_year: 2025, fiscal_period: "FY", period_type: "annual", period_start: "2025-01-01", period_end: "2025-12-31", metrics: { revenue: [value] } };
const quarterly: SecStatementPeriod = { fiscal_year: 2026, fiscal_period: "Q3", period_type: "quarterly", period_start: "2026-07-01", period_end: "2026-09-30", metrics: { revenue: [{ ...value, period_start: "2026-07-01", period_end: "2026-09-30", duration_days: 92, comparison_percent: null, comparison_period_end: null }] } };
const ytd: SecStatementPeriod = { fiscal_year: 2026, fiscal_period: "Q3", period_type: "ytd", period_start: "2026-01-01", period_end: "2026-09-30", metrics: { operating_cash_flow: [{ ...value, field: "operating_cash_flow", period_start: "2026-01-01", period_end: "2026-09-30", duration_days: 273, form: "10-Q", comparison_percent: null, comparison_period_end: null }] } };
const report = { annual_periods: [annual], quarterly_periods: [quarterly], ytd_periods: [ytd], missing_fields: ["stockholders_equity"] } as unknown as SecCompanyReport;

describe("SEC financial statements", () => {
  it("shows annual values, comparable change, and exact SEC provenance", () => {
    render(<SecFinancialStatements report={report} />);
    expect(screen.getByRole("heading", { name: "FY 2025" })).toBeTruthy();
    expect(screen.getByText("100000000.25")).toBeTruthy();
    expect(screen.getByText("+25.00% YoY")).toBeTruthy();
    fireEvent.click(screen.getByText("SEC source"));
    expect(screen.getByText(/us-gaap/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open SEC filing document" }).getAttribute("href")).toContain("sec.gov/Archives");
    expect(screen.getAllByText(/stockholders_equity/).length).toBeGreaterThan(0);
  });

  it("keeps standalone quarters separate from cumulative YTD disclosures", () => {
    render(<SecFinancialStatements report={report} />);
    fireEvent.click(screen.getByRole("button", { name: "Quarterly" }));
    expect(screen.getAllByText("Q3 FY2026").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Year-to-date disclosures" })).toBeTruthy();
    expect(screen.getByText(/kept separate from standalone quarters/)).toBeTruthy();
    expect(screen.getAllByText("YoY unavailable").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Total assets")).toHaveLength(1);
  });

  it("labels missing period values unavailable instead of zero", () => {
    const unavailable = { ...report, annual_periods: [], quarterly_periods: [], ytd_periods: [] } as SecCompanyReport;
    render(<SecFinancialStatements report={unavailable} />);
    expect(screen.getByText("Annual data unavailable")).toBeTruthy();
    expect(screen.getByText(/No missing values have been filled or derived/)).toBeTruthy();
  });
});
