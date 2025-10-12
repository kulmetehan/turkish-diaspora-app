-- UNIQUE op locations.place_id
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'uq_locations_place_id'
  ) then
    alter table public.locations
      add constraint uq_locations_place_id unique (place_id);
  end if;
end $$;

-- Foreign keys voor ai_logs (optioneel ON DELETE SET NULL)
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'fk_ai_logs_task'
  ) then
    alter table public.ai_logs
      add constraint fk_ai_logs_task
      foreign key (task_id) references public.tasks(id) on delete set null;
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'fk_ai_logs_location'
  ) then
    alter table public.ai_logs
      add constraint fk_ai_logs_location
      foreign key (location_id) references public.locations(id) on delete set null;
  end if;
end $$;

-- (optioneel) categoriale referentie vanuit locations naar category_icon_map
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'fk_locations_category_icon'
  ) then
    alter table public.locations
      add constraint fk_locations_category_icon
      foreign key (category) references public.category_icon_map(category) on delete set null;
  end if;
end $$;
