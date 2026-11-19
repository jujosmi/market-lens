import { beforeEach, describe, expect, it } from "vitest";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database, WatchlistItemRow } from "./database.types";
import { createWatchlistRepository, normalizeExchange, normalizeTicker } from "./watchlistRepository";

const rows: WatchlistItemRow[] = [];

function mockRlsClient(authenticatedUserId: string) {
  return {
    from() {
      const filters: Record<string, string> = {};
      let deleting = false;
      const builder: any = {
        select() { return builder; },
        eq(column: string, value: string) { filters[column] = value; return builder; },
        order() {
          return Promise.resolve({
            data: rows.filter((row) => row.user_id === authenticatedUserId && row.user_id === filters.user_id)
              .sort((a, b) => a.created_at.localeCompare(b.created_at)),
            error: null,
          });
        },
        upsert(input: Omit<WatchlistItemRow, "id" | "created_at" | "updated_at"> | Omit<WatchlistItemRow, "id" | "created_at" | "updated_at">[]) {
          const entries = Array.isArray(input) ? input : [input];
          if (entries.some((entry) => entry.user_id !== authenticatedUserId)) return Promise.resolve({ error: { message: "row policy violation" } });
          for (const entry of entries) {
            const duplicate = rows.some((row) => row.user_id === authenticatedUserId && row.symbol === entry.symbol && row.exchange === entry.exchange);
            if (!duplicate) {
              const now = new Date().toISOString();
              rows.push({ ...entry, id: authenticatedUserId + "-" + entry.symbol + "-" + entry.exchange, created_at: now, updated_at: now });
            }
          }
          return Promise.resolve({ error: null });
        },
        delete() { deleting = true; return builder; },
        then(resolve: (value: { error: null }) => unknown) {
          if (deleting) {
            for (let index = rows.length - 1; index >= 0; index -= 1) {
              if (rows[index]?.user_id === authenticatedUserId && rows[index]?.id === filters.id && rows[index]?.user_id === filters.user_id) rows.splice(index, 1);
            }
          }
          return Promise.resolve(resolve({ error: null }));
        },
      };
      return builder;
    },
  } as unknown as SupabaseClient<Database>;
}

describe("authenticated watchlist client scoping (offline RLS model)", () => {
  beforeEach(() => { rows.length = 0; });

  it("normalizes symbols and exchange IDs and prevents duplicate saved entries", async () => {
    const client = mockRlsClient("user-a");
    const repository = createWatchlistRepository(client, "user-a");
    await repository.add(" nvda ", "nasdaq");
    await repository.add("NVDA", "NASDAQ");
    expect(await repository.list()).toMatchObject([{ symbol: "NVDA", exchange: "NASDAQ" }]);
    expect(normalizeTicker("msft")).toBe("MSFT");
    expect(normalizeExchange("nyse")).toBe("NYSE");
    expect(() => normalizeTicker("bad symbol")).toThrow("valid symbol");
    expect(() => normalizeExchange("a venue with spaces")).toThrow("exchange identifier");
  });

  it("treats exchange-qualified listings as separate identities and imports without replacing account rows", async () => {
    const repository = createWatchlistRepository(mockRlsClient("user-a"), "user-a");
    await repository.add("AAPL", "NASDAQ");
    await repository.add("AAPL", "NYSE");
    await repository.importSymbols(["MSFT", "MSFT", "AAPL"], { MSFT: "NASDAQ", AAPL: "NASDAQ" });
    expect(await repository.list()).toMatchObject([
      { symbol: "AAPL", exchange: "NASDAQ" },
      { symbol: "AAPL", exchange: "NYSE" },
      { symbol: "MSFT", exchange: "NASDAQ" },
    ]);
  });

  it("isolates two mock identities and rejects attempts to write for another owner", async () => {
    const userA = mockRlsClient("user-a");
    const userB = mockRlsClient("user-b");
    const watchlistA = createWatchlistRepository(userA, "user-a");
    const watchlistB = createWatchlistRepository(userB, "user-b");
    await watchlistA.add("AAPL", "NASDAQ");
    await watchlistB.add("MSFT", "NASDAQ");
    expect((await watchlistA.list()).map((row) => row.symbol)).toEqual(["AAPL"]);
    expect((await watchlistB.list()).map((row) => row.symbol)).toEqual(["MSFT"]);
    const spoofed = await userA.from("watchlist_items").upsert({ user_id: "user-b", symbol: "AMZN", exchange: "NASDAQ" });
    expect(spoofed.error).toMatchObject({ message: "row policy violation" });
    await watchlistA.remove("user-b-MSFT-NASDAQ");
    expect((await watchlistB.list()).map((row) => row.symbol)).toEqual(["MSFT"]);
  });

  it("requires an authenticated owner before constructing a repository", () => {
    expect(() => createWatchlistRepository(mockRlsClient(""), "")).toThrow("authenticated user");
  });
});
