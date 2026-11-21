import type { SecWatchlistActivityEntry } from "./apiClient";

export type SecFilingReviewSnapshot = {
  version: 1;
  issuers: Record<string, { accessions: string[]; reviewed_at: string }>;
};

const REVIEW_STORAGE_PREFIX = "jujosmi_trade_sec_filing_review_v1:";

function storageKey(scope: string) {
  return REVIEW_STORAGE_PREFIX + encodeURIComponent(scope);
}

export function readSecFilingReviewSnapshot(scope: string): SecFilingReviewSnapshot | null {
  try {
    const raw = window.sessionStorage.getItem(storageKey(scope));
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (value === null || typeof value !== "object") return null;
    const snapshot = value as Partial<SecFilingReviewSnapshot>;
    if (snapshot.version !== 1 || snapshot.issuers === null || typeof snapshot.issuers !== "object") return null;
    const issuers: SecFilingReviewSnapshot["issuers"] = {};
    for (const [cik, item] of Object.entries(snapshot.issuers)) {
      if (!/^[0-9]{10}$/.test(cik) || item === null || typeof item !== "object") continue;
      if (!Array.isArray(item.accessions) || !item.accessions.every((id) => typeof id === "string")
          || typeof item.reviewed_at !== "string") continue;
      issuers[cik] = { accessions: Array.from(new Set(item.accessions)).slice(0, 100), reviewed_at: item.reviewed_at };
    }
    return { version: 1, issuers };
  } catch {
    return null;
  }
}

export function writeSecFilingReviewSnapshot(scope: string, snapshot: SecFilingReviewSnapshot): boolean {
  try {
    window.sessionStorage.setItem(storageKey(scope), JSON.stringify(snapshot));
    return true;
  } catch {
    return false;
  }
}

export function accessionsNewSinceReview(
  snapshot: SecFilingReviewSnapshot | null,
  cik: string,
  accessions: readonly string[],
): Set<string> | null {
  const previous = snapshot?.issuers[cik]?.accessions;
  if (!previous) return null;
  const known = new Set(previous);
  return new Set(accessions.filter((accession) => !known.has(accession)));
}

export function markSuccessfulFilingsReviewed(
  snapshot: SecFilingReviewSnapshot | null,
  entries: readonly SecWatchlistActivityEntry[],
  reviewedAt: string,
): SecFilingReviewSnapshot {
  const issuers = { ...(snapshot?.issuers ?? {}) };
  for (const entry of entries) {
    if (entry.status !== "ok" || !entry.data) continue;
    const accessions = Array.from(new Set(entry.data.filings.map((filing) => filing.accession_number))).slice(0, 100);
    issuers[entry.data.cik] = { accessions, reviewed_at: reviewedAt };
  }
  return { version: 1, issuers };
}
