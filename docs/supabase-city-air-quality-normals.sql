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
