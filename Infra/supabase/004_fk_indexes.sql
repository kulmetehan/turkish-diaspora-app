-- Idempotent FK-indexen
create index if not exists idx_ai_logs_location_id
  on public.ai_logs (location_id);

create index if not exists idx_tasks_location_id
  on public.tasks (location_id);

create index if not exists idx_training_data_location_id
  on public.training_data (location_id);
