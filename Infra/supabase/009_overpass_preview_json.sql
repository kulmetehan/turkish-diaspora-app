DO $$
BEGIN
  -- Add raw_preview_json column if it does not exist
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'overpass_calls'
      AND column_name = 'raw_preview_json'
  ) THEN
    ALTER TABLE public.overpass_calls
      ADD COLUMN raw_preview_json jsonb;
  END IF;

  -- Add comment if column exists (guarded to be idempotent)
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'overpass_calls'
      AND column_name = 'raw_preview_json'
  ) THEN
    COMMENT ON COLUMN public.overpass_calls.raw_preview_json IS 'Compact, always-valid JSON summary of the Overpass response (e.g. first N elements).';
  END IF;
END
$$;








