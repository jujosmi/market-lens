import type { SecCompanyReport, SecStatementMetric, SecStatementPeriod } from "./apiClient";

export type SecResearchMetric = {
  key: string;
  label: string;
  value: string;
  formula: string;
  period: string;
  sources: SecStatementMetric[];
};

function periodName(period: SecStatementPeriod) {
  return period.period_type === "annual"
    ? `FY ${period.fiscal_year ?? "unavailable"}`
    : `${period.fiscal_period ?? "Fiscal period unavailable"} FY${period.fiscal_year ?? ""}`;
}

function singleMetric(period: SecStatementPeriod, field: string, unit?: string): SecStatementMetric | null {
  const matches = (period.metrics[field] ?? []).filter((row) => !unit || row.unit === unit);
  const unique = new Map(matches.map((row) => [`${row.unit}:${row.original_value}:${row.period_start ?? "instant"}:${row.period_end}`, row]));
  // If the SEC response contains conflicting same-unit values, omit the derived result.
  if (!unit && new Set(matches.map((row) => row.unit)).size > 1) {
    const currency = matches.filter((row) => row.currency === "USD");
    if (currency.length) return singleMetric(period, field, currency[0]!.unit);
  }
  return unique.size === 1 ? [...unique.values()][0]! : null;
}

function amount(metric: SecStatementMetric): number | null {
  const value = Number(metric.original_value);
  return Number.isFinite(value) ? value : null;
}

function sourcePeriod(metrics: SecStatementMetric[]): SecResearchMetric["sources"] | null {
  if (!metrics.length || metrics.some((metric) => metric.unit !== metrics[0]!.unit
    || metric.period_start !== metrics[0]!.period_start || metric.period_end !== metrics[0]!.period_end)) return null;
  return metrics;
}

function makeMetric(key: string, label: string, value: number, unit: string, formula: string,
  period: SecStatementPeriod, sources: SecStatementMetric[]): SecResearchMetric {
  const number = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  const formatted = unit === "%" ? `${number}%` : unit === "USD" ? `$${number} USD` : `${number} ${unit}`;
  return { key, label, value: formatted, formula, period: `${periodName(period)} · ${period.period_start ?? "As of"} – ${period.period_end}`, sources };
}

/**
 * Derived summaries use only statement periods already classified by the SEC
 * adapter. No YTD-to-quarter subtraction, cross-currency joins, or tag guesses.
 */
export function buildSecResearchMetrics(report: SecCompanyReport): SecResearchMetric[] {
  const output: SecResearchMetric[] = [];
  const periodGroups = [report.annual_periods ?? [], report.quarterly_periods ?? []];
  for (const periods of periodGroups) {
    for (const current of periods.slice(0, 5)) {
      const revenue = singleMetric(current, "revenue");
      const operating = singleMetric(current, "operating_income", revenue?.unit);
      const netIncome = singleMetric(current, "net_income", revenue?.unit);
      const ocf = singleMetric(current, "operating_cash_flow", revenue?.unit);
      const capex = singleMetric(current, "capital_expenditures", revenue?.unit);

      if (revenue && current.fiscal_year !== null && current.fiscal_year !== undefined) {
        const priorPeriod = periods.find((period) => {
          if (period.fiscal_year !== current.fiscal_year! - 1 || period.fiscal_period !== current.fiscal_period) return false;
          const candidate = singleMetric(period, "revenue", revenue.unit);
          return candidate?.duration_days !== null && candidate?.duration_days !== undefined
            && revenue.duration_days !== null && revenue.duration_days !== undefined
            && Math.abs(candidate.duration_days - revenue.duration_days) <= 7;
        });
        const priorRevenue = priorPeriod ? singleMetric(priorPeriod, "revenue", revenue.unit) : null;
        const now = amount(revenue);
        const before = priorRevenue ? amount(priorRevenue) : null;
        if (now !== null && before !== null && before !== 0) {
          const sources = sourcePeriod([revenue]) && sourcePeriod([priorRevenue!]);
          if (sources) output.push(makeMetric(`revenue-growth-${current.period_type}-${current.period_end}`, "Revenue year-over-year", (now - before) / Math.abs(before) * 100, "%", `(${revenue.original_value} ${revenue.unit} − ${priorRevenue!.original_value} ${priorRevenue!.unit}) ÷ |${priorRevenue!.original_value}| × 100`, current, [revenue, priorRevenue!]));
        }
      }

      for (const [field, source, label] of [["operating_margin", operating, "Operating profit margin"], ["net_margin", netIncome, "Net profit margin"]] as const) {
        if (!source || !revenue) continue;
        const pair = sourcePeriod([source, revenue]);
        const numerator = amount(source); const denominator = amount(revenue);
        if (pair && numerator !== null && denominator !== null && denominator !== 0) {
          output.push(makeMetric(`${field}-${current.period_type}-${current.period_end}`, label, numerator / denominator * 100, "%", `(${source.original_value} ${source.unit} ÷ ${revenue.original_value} ${revenue.unit}) × 100`, current, [source, revenue]));
        }
      }

      if (ocf && capex) {
        const pair = sourcePeriod([ocf, capex]);
        const operatingCash = amount(ocf); const expenditure = amount(capex);
        if (pair && operatingCash !== null && expenditure !== null) {
          output.push(makeMetric(`free-cash-flow-${current.period_type}-${current.period_end}`, "Free cash flow", operatingCash - Math.abs(expenditure), ocf.unit, `${ocf.original_value} ${ocf.unit} − |${capex.original_value} ${capex.unit}|`, current, [ocf, capex]));
        }
      }
    }
  }
  return output;
}

export function reportableBalanceSheetContext(report: SecCompanyReport) {
  const period = (report.annual_periods ?? []).find((item) => item.period_type === "annual")
    ?? (report.quarterly_periods ?? []).find((item) => item.period_type === "quarterly");
  if (!period) return [];
  return [
    ["Cash and cash equivalents", singleMetric(period, "cash_and_equivalents")],
    ["Current long-term debt", singleMetric(period, "long_term_debt_current")],
    ["Noncurrent long-term debt", singleMetric(period, "long_term_debt_noncurrent")],
  ].filter((row): row is [string, SecStatementMetric] => row[1] !== null);
}
