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
