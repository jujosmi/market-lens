import migration from "../../supabase/migrations/202611150001_watchlist_items.sql?raw";
import { describe, expect, it } from "vitest";

const sql = migration.toLowerCase();

describe("watchlist migration security contract (static checks)", () => {
  it("enables RLS and grants only the operations used by the client", () => {
    expect(sql).toMatch(/alter table public\.watchlist_items enable row level security/);
    expect(sql).toMatch(/revoke all privileges on table public\.watchlist_items from public, anon, authenticated/);
    expect(sql).toMatch(/grant select, insert, delete on table public\.watchlist_items to authenticated/);
    expect(sql).not.toMatch(/grant[^;]*\bupdate\b[^;]*on table public\.watchlist_items/);
    expect(sql).toMatch(/unique \(user_id, symbol, exchange\)/);
  });

  it("binds each retained data policy to the authenticated owner", () => {
    for (const action of ["select", "insert", "delete"]) {
      const statement = sql.match(new RegExp(`create policy watchlist_items_${action}_own[\\s\\S]*?;`))?.[0];
      expect(statement).toContain(`for ${action} to authenticated`);
      expect(statement).toContain("auth.uid() is not null and user_id = auth.uid()");
    }
    expect(sql).not.toMatch(/create policy watchlist_items_update_own/);
  });
});
