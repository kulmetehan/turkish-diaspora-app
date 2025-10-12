-- LOCATIONS
create table if not exists public.locations (
  id            uuid primary key default gen_random_uuid(),
  place_id      text not null,
  name          text,
  address       text,
  city          text,
  state         text,
  country       text,
  lat           numeric(9,6),
  lng           numeric(9,6),
  category      text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- AI_LOGS
create table if not exists public.ai_logs (
  id            bigserial primary key,
  event_time    timestamptz not null default now(),
  level         text,
  message       text,
  meta          jsonb,
  task_id       uuid,
  location_id   uuid
);

-- TASKS
create table if not exists public.tasks (
  id            uuid primary key default gen_random_uuid(),
  type          text,
  state         text,
  next_check_at timestamptz,
  payload       jsonb,
  result        jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- TRAINING_DATA
create table if not exists public.training_data (
  id            bigserial primary key,
  prompt        text not null,
  completion    text not null,
  tags          text[] default '{}',
  created_at    timestamptz not null default now()
);

-- CATEGORY_ICON_MAP
create table if not exists public.category_icon_map (
  category      text primary key,
  icon_name     text not null
);
