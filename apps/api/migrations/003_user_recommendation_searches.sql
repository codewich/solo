create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  name text,
  image_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists user_auth_accounts (
  id bigserial primary key,
  user_id uuid not null references users(id) on delete cascade,
  provider text not null,
  provider_subject text not null,
  created_at timestamptz not null default now(),
  unique (provider, provider_subject)
);

create table if not exists travel_windows (
  id text primary key,
  user_id uuid not null references users(id) on delete cascade,
  label text,
  start_date date not null,
  end_date date not null,
  status text not null default 'candidate',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists recommendation_searches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  travel_window_id text not null references travel_windows(id) on delete cascade,
  home_city_id text not null references cities(id),
  radius_km integer not null,
  min_population integer not null,
  candidate_limit integer not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, travel_window_id)
);

create table if not exists recommendation_excluded_cities (
  search_id uuid not null references recommendation_searches(id) on delete cascade,
  city_id text not null references cities(id) on delete cascade,
  primary key (search_id, city_id)
);

create table if not exists recommendation_results (
  search_id uuid not null references recommendation_searches(id) on delete cascade,
  city_id text not null references cities(id) on delete cascade,
  score integer not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (search_id, city_id)
);

create index if not exists recommendation_results_score_idx
  on recommendation_results (search_id, score desc);
