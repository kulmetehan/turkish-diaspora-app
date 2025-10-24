DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'tasks'
      AND column_name = 'is_success'
  ) THEN
    ALTER TABLE public.tasks
    ADD COLUMN is_success boolean;
    COMMENT ON COLUMN public.tasks.is_success IS 'Optional success flag for task outcome (mirrors status).';
  END IF;
END
$$;


