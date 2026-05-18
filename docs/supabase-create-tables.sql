-- Solo Supabase schema.
-- Run this in the Supabase SQL editor.

create extension if not exists postgis with schema extensions;

create table if not exists public.countries (
  code text primary key,
  name text not null,
  region text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.cities (
  id text primary key,
  name text not null,
  asciiname text,
  alternatenames text,
  country_code text,
  country_name text not null,
  region text,
  feature_class text,
  feature_code text,
  admin1_code text,
  admin2_code text,
  admin3_code text,
  admin4_code text,
  timezone text,
  latitude double precision not null,
  longitude double precision not null,
  population integer,
  dem integer,
  geonames_modified_at date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists cities_location_gix
  on public.cities using gist (extensions.geography(extensions.ST_MakePoint(longitude, latitude)));
create index if not exists cities_country_code_idx on public.cities (country_code);
create index if not exists cities_population_idx on public.cities (population);
create index if not exists cities_name_idx on public.cities (name);
create index if not exists cities_admin1_code_idx on public.cities (admin1_code);
create index if not exists cities_feature_code_idx on public.cities (feature_code);

create table if not exists public.airports (
  id text primary key,
  iata_code text unique,
  name text not null,
  city_id text references public.cities(id) on delete set null,
  country_code text,
  latitude double precision not null,
  longitude double precision not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.attractions (
  id bigserial primary key,
  city_id text references public.cities(id) on delete cascade,
  name text not null,
  latitude double precision,
  longitude double precision,
  attraction_type text not null,
  source text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists attractions_city_id_idx on public.attractions (city_id);

create table if not exists public.climate_normals (
  id bigserial primary key,
  city_id text not null references public.cities(id) on delete cascade,
  month smallint not null check (month between 1 and 12),
  avg_temp_min double precision,
  avg_temp_max double precision,
  rainfall double precision,
  sunshine_hours double precision,
  source text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (city_id, month, source)
);

create table if not exists public.city_air_quality_normals (
  city_id text not null references public.cities(id) on delete cascade,
  year integer not null check (year between 2000 and 2100),
  month smallint not null check (month between 1 and 12),
  european_aqi double precision,
  us_aqi double precision,
  pm25 double precision,
  pm10 double precision,
  no2 double precision,
  source text not null default 'Open-Meteo',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (city_id, year, month)
);

create index if not exists city_air_quality_normals_city_month_idx
  on public.city_air_quality_normals (city_id, year, month);

create table if not exists public.recommendation_scores (
  id bigserial primary key,
  city_id text not null references public.cities(id) on delete cascade,
  travel_window_id text not null,
  climate_score integer not null,
  attraction_score integer not null,
  popularity_score integer not null,
  air_quality_score integer not null default 0,
  final_score integer not null,
  calculated_at timestamptz not null default now(),
  unique (city_id, travel_window_id)
);

create index if not exists recommendation_scores_final_score_idx
  on public.recommendation_scores (final_score desc);

alter table if exists public.recommendation_scores
  drop column if exists affordability_score;

create table if not exists public.user_saved_destinations (
  id bigserial primary key,
  user_id text not null,
  city_id text not null references public.cities(id) on delete cascade,
  status text not null default 'saved',
  created_at timestamptz not null default now(),
  unique (user_id, city_id)
);

create table if not exists public.flight_alerts (
  id bigserial primary key,
  user_id text not null,
  origin_airport_id text references public.airports(id) on delete set null,
  destination_city_id text references public.cities(id) on delete cascade,
  max_price numeric,
  currency text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.flight_price_snapshots (
  id bigserial primary key,
  origin_airport_id text references public.airports(id) on delete set null,
  destination_city_id text references public.cities(id) on delete cascade,
  departure_date date,
  return_date date,
  price numeric,
  currency text,
  provider text not null,
  payload jsonb not null default '{}'::jsonb,
  captured_at timestamptz not null default now()
);

create table if not exists public.hotel_price_snapshots (
  id bigserial primary key,
  city_id text references public.cities(id) on delete cascade,
  check_in_date date,
  check_out_date date,
  median_nightly_price numeric,
  average_nightly_price numeric,
  currency text,
  provider text not null,
  payload jsonb not null default '{}'::jsonb,
  captured_at timestamptz not null default now()
);

create table if not exists public.api_cache (
  cache_key text primary key,
  provider text not null,
  payload jsonb not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists api_cache_expires_at_idx on public.api_cache (expires_at);

create table if not exists public.holiday_regions (
  provider text not null default 'calendarific',
  country_code text not null,
  region_code text not null,
  name text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (provider, country_code, region_code)
);

create table if not exists public.holiday_region_cache_status (
  provider text not null default 'calendarific',
  country_code text not null,
  status text not null,
  error_message text,
  fetched_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (provider, country_code)
);

create table if not exists public.public_holidays (
  provider text not null default 'calendarific',
  country_code text not null,
  region_code text not null default '',
  year integer not null,
  holiday_date date not null,
  name text not null,
  holiday_type text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (provider, country_code, region_code, year, holiday_date, name)
);

create index if not exists public_holidays_lookup_idx
  on public.public_holidays (country_code, region_code, year, holiday_date);

insert into public.holiday_regions (provider, country_code, region_code, name, payload)
values
  ('calendarific', 'GB', 'gb-eng', 'England', '{"source":"static-region-options"}'::jsonb),
  ('calendarific', 'GB', 'gb-wls', 'Wales', '{"source":"static-region-options"}'::jsonb),
  ('calendarific', 'GB', 'gb-sct', 'Scotland', '{"source":"static-region-options"}'::jsonb),
  ('calendarific', 'GB', 'gb-nir', 'Northern Ireland', '{"source":"static-region-options"}'::jsonb)
on conflict (provider, country_code, region_code) do update set
  name = excluded.name,
  payload = excluded.payload,
  updated_at = now();

insert into public.holiday_region_cache_status (provider, country_code, status)
values ('calendarific', 'GB', 'ready')
on conflict (provider, country_code) do update set
  status = excluded.status,
  error_message = null,
  fetched_at = now(),
  updated_at = now();

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.users (
  id uuid primary key default extensions.gen_random_uuid(),
  email text unique,
  name text,
  image_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_auth_accounts (
  id bigserial primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  provider text not null,
  provider_subject text not null,
  created_at timestamptz not null default now(),
  unique (provider, provider_subject)
);

create table if not exists public.travel_windows (
  id text primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  label text,
  start_date date not null,
  end_date date not null,
  status text not null default 'candidate',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table if exists public.recommendation_searches
  drop constraint if exists recommendation_searches_travel_window_id_fkey;

alter table if exists public.travel_windows
  drop constraint if exists travel_windows_pkey;

create table if not exists public.recommendation_searches (
  id uuid primary key default extensions.gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  travel_window_id text not null,
  home_city_id text not null references public.cities(id),
  radius_km integer not null,
  min_population integer not null,
  candidate_limit integer not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, travel_window_id)
);

insert into public.travel_windows (id, user_id, label, start_date, end_date, status, created_at, updated_at)
select
  search.travel_window_id,
  search.user_id,
  travel_window.label,
  travel_window.start_date,
  travel_window.end_date,
  travel_window.status,
  now(),
  now()
from public.recommendation_searches search
join public.travel_windows travel_window on travel_window.id = search.travel_window_id
left join public.travel_windows owned_window
  on owned_window.id = search.travel_window_id
  and owned_window.user_id = search.user_id
where owned_window.id is null;

alter table if exists public.travel_windows
  add constraint travel_windows_pkey primary key (user_id, id);

alter table if exists public.recommendation_searches
  add constraint recommendation_searches_user_travel_window_fkey
  foreign key (user_id, travel_window_id)
  references public.travel_windows(user_id, id)
  on delete cascade;

alter table if exists public.recommendation_searches
  add constraint recommendation_searches_id_user_id_key unique (id, user_id);

create table if not exists public.recommendation_excluded_cities (
  search_id uuid not null references public.recommendation_searches(id) on delete cascade,
  city_id text not null references public.cities(id) on delete cascade,
  primary key (search_id, city_id)
);

create table if not exists public.recommendation_results (
  search_id uuid not null references public.recommendation_searches(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  city_id text not null references public.cities(id) on delete cascade,
  score integer not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (search_id, city_id),
  foreign key (search_id, user_id)
    references public.recommendation_searches(id, user_id)
    on delete cascade
);

create index if not exists recommendation_results_score_idx
  on public.recommendation_results (search_id, score desc);

create index if not exists recommendation_results_user_score_idx
  on public.recommendation_results (user_id, score desc);
