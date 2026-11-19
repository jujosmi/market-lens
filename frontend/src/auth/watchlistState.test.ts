import { describe, expect, it } from "vitest";
import { accountWatchlistForUser, accountWatchlistIsLoading } from "./watchlistState";

const row = { id: "row-a", symbol: "AAPL", exchange: "NASDAQ", created_at: "2026-11-18T00:00:00Z", updated_at: "2026-11-18T00:00:00Z" };

describe("account-scoped watchlist view state", () => {
  it("never exposes cached rows to a signed-out or different account view", () => {
    const state = { ownerId: "user-a", rows: [row], loading: false, error: "" };
    expect(accountWatchlistForUser(state, "user-a")).toEqual([row]);
    expect(accountWatchlistForUser(state, "user-b")).toEqual([]);
    expect(accountWatchlistForUser(state, null)).toEqual([]);
    expect(accountWatchlistIsLoading(state, "user-b")).toBe(true);
  });
});
