alter table public.recommendation_searches
  add column if not exists search_mode text not null default 'radius';

alter table public.recommendation_searches
  add column if not exists search_bounds jsonb;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'recommendation_searches_search_mode_check'
  ) then
    alter table public.recommendation_searches
      add constraint recommendation_searches_search_mode_check
      check (search_mode in ('radius', 'rectangle'));
  end if;
end $$;

create index if not exists recommendation_searches_search_mode_idx
  on public.recommendation_searches (search_mode);
