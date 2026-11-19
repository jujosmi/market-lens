import type { WatchlistEntry } from "./watchlistRepository";

export type AccountWatchlistState = { ownerId: string | null; rows: WatchlistEntry[]; loading: boolean; error: string };

export function accountWatchlistForUser(state: AccountWatchlistState, userId: string | null): WatchlistEntry[] {
  return userId && state.ownerId === userId ? state.rows : [];
}

export function accountWatchlistIsLoading(state: AccountWatchlistState, userId: string | null): boolean {
  return Boolean(userId && (state.ownerId !== userId || state.loading));
}
