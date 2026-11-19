import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database, WatchlistItemRow } from "./database.types";

export type WatchlistEntry = Pick<WatchlistItemRow, "id" | "symbol" | "exchange" | "created_at" | "updated_at">;

export function normalizeTicker(symbol: string) {
  const normalized = symbol.trim().toUpperCase();
  if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(normalized)) throw new Error("Ticker must be a valid symbol of 1 to 10 characters.");
  return normalized;
}

export function normalizeExchange(exchange?: string | null) {
  const normalized = exchange?.trim().toUpperCase() ?? "";
  if (normalized && !/^[A-Z0-9._-]{1,20}$/.test(normalized)) throw new Error("Exchange must use a valid exchange identifier.");
  return normalized;
}

function safeDatabaseError() {
  return new Error("The saved watchlist could not be synchronized. Check your sign-in and try again.");
}

export function createWatchlistRepository(client: SupabaseClient<Database>, ownerId: string) {
  if (!ownerId) throw new Error("An authenticated user is required.");

  return {
    async list(): Promise<WatchlistEntry[]> {
      const { data, error } = await client.from("watchlist_items")
        .select("id,user_id,symbol,exchange,created_at,updated_at")
        .eq("user_id", ownerId)
        .order("created_at", { ascending: true });
      if (error || !data) throw safeDatabaseError();
      if (data.some((row) => row.user_id !== ownerId)) throw new Error("The saved watchlist returned an unexpected owner.");
      return data.map(({ id, symbol, exchange, created_at, updated_at }) => ({ id, symbol, exchange, created_at, updated_at }));
    },

    async add(symbol: string, exchange?: string | null): Promise<void> {
      const { error } = await client.from("watchlist_items").upsert({
        user_id: ownerId,
        symbol: normalizeTicker(symbol),
        exchange: normalizeExchange(exchange),
      }, { onConflict: "user_id,symbol,exchange", ignoreDuplicates: true });
      if (error) throw safeDatabaseError();
    },

    async remove(id: string): Promise<void> {
      const { error } = await client.from("watchlist_items").delete().eq("id", id).eq("user_id", ownerId);
      if (error) throw safeDatabaseError();
    },

    async importSymbols(symbols: string[], exchangeBySymbol: Record<string, string | null | undefined> = {}): Promise<void> {
      const unique = new Map<string, { user_id: string; symbol: string; exchange: string }>();
      for (const raw of symbols) {
        const symbol = normalizeTicker(raw);
        const exchange = normalizeExchange(exchangeBySymbol[symbol]);
        unique.set(`${symbol}\u0000${exchange}`, { user_id: ownerId, symbol, exchange });
      }
      const entries = [...unique.values()];
      if (!entries.length) return;
      const { error } = await client.from("watchlist_items").upsert(entries, {
        onConflict: "user_id,symbol,exchange",
        ignoreDuplicates: true,
      });
      if (error) throw safeDatabaseError();
    },
  };
}
