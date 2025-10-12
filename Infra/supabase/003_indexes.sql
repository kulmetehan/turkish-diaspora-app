-- Veelgebruikte zoekvelden / FK indexes
create index if not exists idx_locations_state        on public.locations(state);
create index if not exists idx_locations_category     on public.locations(category);
create index if not exists idx_ai_logs_task_id        on public.ai_logs(task_id);
create index if not exists idx_ai_logs_location_id    on public.ai_logs(location_id);
create index if not exists idx_tasks_state            on public.tasks(state);
create index if not exists idx_tasks_next_check_at    on public.tasks(next_check_at);
