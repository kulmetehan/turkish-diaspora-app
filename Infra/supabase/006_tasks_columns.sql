DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'tasks'
      AND column_name = 'is_success'
  ) THEN
    ALTER TABLE public.tasks ADD COLUMN is_success boolean;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'tasks'
      AND column_name = 'error_message'
  ) THEN
    ALTER TABLE public.tasks ADD COLUMN error_message text;
  END IF;
END
$$;


