export type TickerFixture = {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  price: string;
  change: string;
  changeTone: "up" | "down";
  series: number[];
  strength: number;
  range: string;
};

export const tickerFixtures: TickerFixture[] = [
  { symbol: "NVDA", name: "NVIDIA Corporation", exchange: "NASDAQ", sector: "Technology", industry: "Semiconductors", price: "142.68", change: "+1.84%", changeTone: "up", series: [30, 33, 29, 37, 34, 40, 38, 45, 41, 49, 45, 54, 51, 58, 55, 65, 61, 70, 67, 76, 73, 81, 77, 86], strength: 72, range: "1M" },
  { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", sector: "Technology", industry: "Consumer Electronics", price: "231.44", change: "+0.62%", changeTone: "up", series: [40, 43, 39, 42, 46, 43, 48, 45, 50, 49, 54, 51, 55, 53, 58, 57, 60, 58, 64, 61, 66, 65, 70, 73], strength: 64, range: "1M" },
  { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", sector: "Technology", industry: "Software Infrastructure", price: "512.24", change: "−0.28%", changeTone: "down", series: [70, 67, 72, 69, 64, 68, 62, 65, 59, 62, 56, 58, 53, 57, 51, 54, 49, 52, 46, 49, 44, 47, 42, 45], strength: 48, range: "1M" },
  { symbol: "AMZN", name: "Amazon.com, Inc.", exchange: "NASDAQ", sector: "Consumer Cyclical", industry: "Internet Retail", price: "218.90", change: "+1.11%", changeTone: "up", series: [32, 35, 33, 38, 36, 39, 37, 45, 42, 47, 44, 50, 47, 53, 50, 56, 53, 60, 57, 65, 62, 68, 64, 74], strength: 68, range: "1M" },
  { symbol: "GOOGL", name: "Alphabet Inc.", exchange: "NASDAQ", sector: "Communication Services", industry: "Internet Content & Information", price: "176.42", change: "+0.43%", changeTone: "up", series: [35, 38, 36, 41, 39, 43, 40, 46, 44, 49, 47, 52, 49, 55, 53, 58, 56, 63, 60, 67, 63, 70, 68, 73], strength: 61, range: "1M" },
  { symbol: "JPM", name: "JPMorgan Chase & Co.", exchange: "NYSE", sector: "Financial Services", industry: "Credit Services", price: "284.16", change: "−0.21%", changeTone: "down", series: [68, 64, 70, 67, 63, 66, 61, 65, 59, 62, 57, 60, 55, 59, 53, 56, 51, 55, 48, 52, 45, 49, 43, 46], strength: 57, range: "1M" },
  { symbol: "LLY", name: "Eli Lilly and Company", exchange: "NYSE", sector: "Healthcare", industry: "Drug Manufacturers", price: "812.30", change: "+0.86%", changeTone: "up", series: [26, 29, 27, 34, 31, 38, 35, 42, 39, 46, 43, 51, 48, 55, 51, 59, 56, 63, 60, 68, 64, 71, 68, 76], strength: 74, range: "1M" },
];

export const pulseFixtures = [
  { name: "S&P 500", symbol: "SPX", value: "5,842.47", change: "+0.38%", tone: "up", series: [18, 22, 20, 28, 25, 33, 30, 38, 36, 43, 40, 46] },
  { name: "NASDAQ 100", symbol: "NDX", value: "20,271.88", change: "+0.61%", tone: "up", series: [16, 20, 19, 27, 25, 34, 31, 40, 38, 46, 43, 52] },
  { name: "DOW JONES", symbol: "DJI", value: "42,215.80", change: "−0.14%", tone: "down", series: [42, 39, 44, 37, 40, 33, 36, 28, 32, 24, 27, 20] },
  { name: "VIX", symbol: "VOLATILITY", value: "17.36", change: "−2.1%", tone: "up", series: [32, 30, 35, 29, 27, 31, 25, 23, 27, 20, 18, 16] },
] as const;

export const chartIntervals = ["1D", "1W", "1M", "3M", "1Y", "ALL"] as const;
export type ChartInterval = (typeof chartIntervals)[number];
export const chartStyles = ["Area", "Line"] as const;
export type ChartStyle = (typeof chartStyles)[number];

export function buildSeries(values: number[], interval: ChartInterval, referencePrice = 100) {
  const factors: Record<ChartInterval, number> = { "1D": 0.28, "1W": 0.52, "1M": 1, "3M": 1.28, "1Y": 1.66, ALL: 2.1 };
  const factor = factors[interval];
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const shaped = values.map((value, index) => mean + (value - mean) * factor + Math.sin(index * 1.6) * factor * 2);
  const span = Math.max(...shaped) - Math.min(...shaped) || 1;
  const scale = (referencePrice * 0.08) / span;
  const latest = shaped.at(-1)!;
  return shaped.map((value) => Number((referencePrice + (value - latest) * scale).toFixed(2)));
}
