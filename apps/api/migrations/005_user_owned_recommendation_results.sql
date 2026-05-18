alter table if exists recommendation_searches
  drop constraint if exists recommendation_searches_travel_window_id_fkey;

alter table if exists travel_windows
  drop constraint if exists travel_windows_pkey;

insert into travel_windows (id, user_id, label, start_date, end_date, status, created_at, updated_at)
select
  search.travel_window_id,
  search.user_id,
  travel_window.label,
  travel_window.start_date,
  travel_window.end_date,
  travel_window.status,
  now(),
  now()
from recommendation_searches search
join travel_windows travel_window on travel_window.id = search.travel_window_id
left join travel_windows owned_window
  on owned_window.id = search.travel_window_id
  and owned_window.user_id = search.user_id
where owned_window.id is null;

alter table if exists travel_windows
  add constraint travel_windows_pkey primary key (user_id, id);

alter table if exists recommendation_searches
  add constraint recommendation_searches_user_travel_window_fkey
  foreign key (user_id, travel_window_id)
  references travel_windows(user_id, id)
  on delete cascade;

alter table if exists recommendation_searches
  add constraint recommendation_searches_id_user_id_key unique (id, user_id);

alter table if exists recommendation_results
  add column if not exists user_id uuid;

update recommendation_results result
set user_id = search.user_id
from recommendation_searches search
where result.search_id = search.id
  and result.user_id is null;

alter table if exists recommendation_results
  alter column user_id set not null;

alter table if exists recommendation_results
  add constraint recommendation_results_user_id_fkey
  foreign key (user_id)
  references users(id)
  on delete cascade;

alter table if exists recommendation_results
  add constraint recommendation_results_search_user_fkey
  foreign key (search_id, user_id)
  references recommendation_searches(id, user_id)
  on delete cascade;

create index if not exists recommendation_results_user_score_idx
  on recommendation_results (user_id, score desc);
