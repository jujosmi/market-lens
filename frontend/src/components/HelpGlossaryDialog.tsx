import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Search } from "lucide-react";
import { ModalPanel } from "./ModalPanel";

const entries = [
  ["Revenue", "The income a company records from selling goods or services before operating costs, interest, and taxes."],
  ["Net income", "The profit or loss remaining after expenses, interest, taxes, and other reported items for a period."],
  ["Operating income", "A reported measure of profit from business operations before non-operating items and income taxes."],
  ["EPS", "Earnings per share. Net income attributable to common shareholders divided by weighted-average shares, subject to the company's reported calculation."],
  ["Assets and liabilities", "Assets are resources reported by a company; liabilities are its reported obligations. Balance-sheet values are measured as of a reporting date."],
  ["10-K", "A company's annual report filed with the SEC. It includes audited annual financial statements and other required disclosures."],
  ["10-Q", "A company's quarterly report filed with the SEC for the first three fiscal quarters. It generally includes unaudited interim financial statements."],
  ["SEC EDGAR", "The U.S. Securities and Exchange Commission's public filing system. Jujosmi's SEC panels show reported filing data with dates and source links."],
  ["Filing date vs. reporting period", "The filing date is when a document was submitted to the SEC. The reporting period is the time span or date the reported financial information covers."],
  ["OHLCV", "Open, high, low, close, and volume: common fields used to describe a trading bar. Jujosmi does not extract these values from the TradingView embed."],
  ["Market capitalization", "A market value measure often calculated as share price multiplied by shares outstanding. It is unavailable here unless a permitted source is connected."],
  ["P/E ratio", "Price-to-earnings ratio: share price divided by earnings per share, using a clearly specified earnings period. Jujosmi does not calculate it from the TradingView widget."],
  ["TradingView charts", "The public chart is an official TradingView embed with its own controls and attribution. Jujosmi does not read, extract, or use widget data to calculate technical ratings."],
  ["Watchlists", "A list of symbols saved for quick access. Guest lists are temporary in this browser session; configured signed-in account storage is separate."],
  ["Synthetic vs. actual financial information", "Synthetic fixtures are illustrative test values and are labeled as samples. SEC facts are actual reported filing observations, not real-time results or forecasts."],
] as const;

const workspaces = [
  ["Market Overview", "Choose an exchange-qualified symbol, view the public TradingView chart, or switch to clearly labeled local demonstration data."],
  ["Discovery", "Browse the local simulated company directory and calendar in demo modes. Public directory listings and event dates are unavailable until an approved source exists."],
  ["Company Research", "Review SEC-reported identity, financial facts, and filing links where available. Analyst, news, and unsupported third-party research features remain unavailable in public mode."],
  ["Watchlist", "Keep supported symbols in a temporary guest list or, when configured, a private account list. Public quote and research values are not supplied by the watchlist."],
] as const;

type Props = { onClose: () => void; initialQuery?: string };

export function HelpGlossaryDialog({ onClose, initialQuery = "" }: Props) {
  const [query, setQuery] = useState(initialQuery);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const filteredEntries = useMemo(() => entries.filter(([term, description]) => `${term} ${description}`.toLowerCase().includes(query.trim().toLowerCase())), [query]);
  const filteredWorkspaces = useMemo(() => workspaces.filter(([name, description]) => `${name} ${description}`.toLowerCase().includes(query.trim().toLowerCase())), [query]);

  function moveResultFocus(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "ArrowDown") return;
    const first = resultsRef.current?.querySelector<HTMLElement>("summary, button");
    if (first) { event.preventDefault(); first.focus(); }
  }

  return <ModalPanel title="Help & glossary" onClose={onClose} className="help-glossary-dialog" initialFocusRef={inputRef}>
    <p className="utility-dialog-intro">Plain-language notes for the four workspaces and their data sources.</p>
    <label className="glossary-search"><Search size={16} /><input ref={inputRef} value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={moveResultFocus} placeholder="Search terms, workspaces, and sources" aria-label="Search help and glossary" /></label>
    <div className="glossary-results" ref={resultsRef}>
      {!query.trim() && <h3>Workspaces</h3>}
      {filteredWorkspaces.map(([name, description]) => <details className="glossary-entry" key={name}><summary>{name}</summary><p>{description}</p></details>)}
      {!query.trim() && <h3>Terms</h3>}
      {filteredEntries.map(([term, description]) => <details className="glossary-entry" key={term}><summary>{term}</summary><p>{description}</p></details>)}
      {!filteredEntries.length && !filteredWorkspaces.length && <p className="glossary-empty" role="status">No matching help topics. Try a shorter search.</p>}
    </div>
    <div className="glossary-source-note"><b>Source boundaries</b><p>Public charts are served by TradingView and stay separate from Jujosmi calculations. SEC panels use filed information with source dates and filing links. Analyst, news, live quotes, and other unapproved sources are not active in public mode.</p></div>
  </ModalPanel>;
}
