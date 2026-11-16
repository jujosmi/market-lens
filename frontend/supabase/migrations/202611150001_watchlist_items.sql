-- Jujosmi Trade UI 2.0 — private account watchlists.
-- Review and apply only to an explicitly approved development project.
begin;

create table if not exists public.watchlist_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  symbol text not null,
  exchange text not null default '',
  created_at timestamptz not null default pg_catalog.now(),
  updated_at timestamptz not null default pg_catalog.now(),
  constraint watchlist_items_symbol_format
    check (symbol = upper(symbol) and symbol ~ '^[A-Z][A-Z0-9.-]{0,9}$'),
  constraint watchlist_items_exchange_format
    check (exchange = '' or (exchange = upper(exchange) and exchange ~ '^[A-Z0-9._-]{1,20}$')),
  constraint watchlist_items_owner_security_unique
    unique (user_id, symbol, exchange)
);

create index if not exists watchlist_items_owner_created_idx
  on public.watchlist_items (user_id, created_at);

create or replace function public.touch_watchlist_item_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $function$
begin
  new.updated_at := pg_catalog.now();
  return new;
end;
$function$;

drop trigger if exists watchlist_items_touch_updated_at on public.watchlist_items;
create trigger watchlist_items_touch_updated_at
before update on public.watchlist_items
for each row execute function public.touch_watchlist_item_updated_at();

alter table public.watchlist_items enable row level security;

-- Revoke implicit/default Data API grants first, then grant only app operations.
revoke all privileges on table public.watchlist_items from public, anon, authenticated;
grant usage on schema public to authenticated;
grant select, insert, delete on table public.watchlist_items to authenticated;

drop policy if exists watchlist_items_select_own on public.watchlist_items;
create policy watchlist_items_select_own
  on public.watchlist_items for select to authenticated
  using (auth.uid() is not null and user_id = auth.uid());

drop policy if exists watchlist_items_insert_own on public.watchlist_items;
create policy watchlist_items_insert_own
  on public.watchlist_items for insert to authenticated
  with check (auth.uid() is not null and user_id = auth.uid());

-- Watchlist rows are immutable through the client; remove any older update policy if rerun.
drop policy if exists watchlist_items_update_own on public.watchlist_items;

drop policy if exists watchlist_items_delete_own on public.watchlist_items;
create policy watchlist_items_delete_own
  on public.watchlist_items for delete to authenticated
  using (auth.uid() is not null and user_id = auth.uid());

comment on table public.watchlist_items is
  'Private user-owned security identifiers only; no prices or market-provider data.';

commit;
