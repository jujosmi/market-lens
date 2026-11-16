import { tickerFixtures } from "./fixtures";

export const sectors = ["All sectors", "Technology", "Consumer Cyclical", "Communication Services", "Healthcare", "Financial Services"] as const;
export const industryBySector: Record<(typeof sectors)[number], string[]> = {
  "All sectors": ["All industries", "Semiconductors", "Consumer Electronics", "Software Infrastructure", "Internet Retail", "Internet Content & Information", "Credit Services"],
  Technology: ["All industries", "Semiconductors", "Consumer Electronics", "Software Infrastructure"],
  "Consumer Cyclical": ["All industries", "Internet Retail"],
  "Communication Services": ["All industries", "Internet Content & Information"],
  Healthcare: ["All industries", "Drug Manufacturers"],
  "Financial Services": ["All industries", "Credit Services"],
};

// Classification and every metric below are deliberately simulated UI fixtures.
export const directoryFixtures = [
  ...tickerFixtures.map((ticker) => ({ ...ticker, marketCap: ticker.symbol === "NVDA" ? "$3.4T" : ticker.symbol === "AAPL" ? "$3.5T" : ticker.symbol === "MSFT" ? "$3.8T" : ticker.symbol === "AMZN" ? "$2.3T" : ticker.symbol === "GOOGL" ? "$2.1T" : ticker.symbol === "JPM" ? "$806B" : "$771B", rating: ticker.strength >= 68 ? "Positive" : ticker.strength >= 50 ? "Balanced" : "Cautious" })),
];

export const companyResearchFixtures = {
  fundamentals: [
    ["Revenue · TTM", "$391.0B", "+12.6% YoY"], ["Operating margin", "45.2%", "Illustrative"], ["Free cash flow", "$72.4B", "TTM sample"], ["P/E · forward", "31.8×", "Illustrative"],
  ],
  quarters: [["Q4 sample", "$124.3B", "$42.1B", "$30.8B"], ["Q3 sample", "$118.6B", "$41.6B", "$26.9B"], ["Q2 sample", "$110.5B", "$39.8B", "$23.1B"]],
  analysts: [["Buy", 64], ["Hold", 29], ["Sell", 7]] as const,
  target: "$184.00", lowTarget: "$142.00", highTarget: "$220.00",
  events: [["Aug 07", "Quarterly earnings call", "After market · illustrative date"], ["Aug 08", "Sample investor conference", "Company event fixture"], ["Sep 12", "Estimated earnings window", "Date is illustrative"]],
  headlines: [
    ["Illustrative headline: company outlines product roadmap", "Sample Wire", "2h", "Neutral"],
    ["Illustrative headline: analysts discuss long-term demand trends", "Market Journal", "5h", "Mixed"],
    ["Illustrative headline: quarterly results preview", "Research Desk", "1d", "Neutral"],
  ],
} as const;

export type DirectoryFixture = (typeof directoryFixtures)[number];

export interface WorkspaceDataSource {
  getTickers: () => typeof tickerFixtures;
  getDirectory: () => typeof directoryFixtures;
  getIndustries: (sector: keyof typeof industryBySector) => string[];
  getResearch: () => typeof companyResearchFixtures;
}

export const fixtureRepository: WorkspaceDataSource = {
  getTickers: () => tickerFixtures,
  getDirectory: () => directoryFixtures,
  getIndustries: (sector: keyof typeof industryBySector) => industryBySector[sector],
  getResearch: () => companyResearchFixtures,
};
