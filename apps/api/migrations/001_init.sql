create extension if not exists postgis;

create table if not exists countries (
  code text primary key,
  name text not null,
  region text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists cities (
  id text primary key,
  name text not null,
  country_code text,
  country_name text not null,
  region text,
  timezone text,
  latitude double precision not null,
  longitude double precision not null,
  population integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists cities_location_gix
  on cities using gist (geography(ST_MakePoint(longitude, latitude)));
create index if not exists cities_country_code_idx on cities (country_code);
create index if not exists cities_population_idx on cities (population);
create index if not exists cities_name_idx on cities (name);

create table if not exists airports (
  id text primary key,
  iata_code text unique,
  name text not null,
  city_id text references cities(id) on delete set null,
  country_code text,
  latitude double precision not null,
  longitude double precision not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists attractions (
  id bigserial primary key,
  city_id text references cities(id) on delete cascade,
  name text not null,
  latitude double precision,
  longitude double precision,
  attraction_type text not null,
  source text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists attractions_city_id_idx on attractions (city_id);

create table if not exists climate_normals (
  id bigserial primary key,
  city_id text not null references cities(id) on delete cascade,
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

create table if not exists city_air_quality_normals (
  city_id text not null references cities(id) on delete cascade,
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
  on city_air_quality_normals (city_id, year, month);

create table if not exists recommendation_scores (
  id bigserial primary key,
  city_id text not null references cities(id) on delete cascade,
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
  on recommendation_scores (final_score desc);

create table if not exists user_saved_destinations (
  id bigserial primary key,
  user_id text not null,
  city_id text not null references cities(id) on delete cascade,
  status text not null default 'saved',
  created_at timestamptz not null default now(),
  unique (user_id, city_id)
);

create table if not exists flight_alerts (
  id bigserial primary key,
  user_id text not null,
  origin_airport_id text references airports(id) on delete set null,
  destination_city_id text references cities(id) on delete cascade,
  max_price numeric,
  currency text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists flight_price_snapshots (
  id bigserial primary key,
  origin_airport_id text references airports(id) on delete set null,
  destination_city_id text references cities(id) on delete cascade,
  departure_date date,
  return_date date,
  price numeric,
  currency text,
  provider text not null,
  payload jsonb not null default '{}'::jsonb,
  captured_at timestamptz not null default now()
);

create table if not exists hotel_price_snapshots (
  id bigserial primary key,
  city_id text references cities(id) on delete cascade,
  check_in_date date,
  check_out_date date,
  median_nightly_price numeric,
  average_nightly_price numeric,
  currency text,
  provider text not null,
  payload jsonb not null default '{}'::jsonb,
  captured_at timestamptz not null default now()
);

create table if not exists api_cache (
  cache_key text primary key,
  provider text not null,
  payload jsonb not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists api_cache_expires_at_idx on api_cache (expires_at);
