-- 033a_fix_chat_notifications_column.sql
-- Fix: Add chat_notifications column if it doesn't exist
-- This migration ensures the column exists even if the table was created before it was added

-- Add chat_notifications column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'push_notification_preferences' 
        AND column_name = 'chat_notifications'
    ) THEN
        ALTER TABLE public.push_notification_preferences
        ADD COLUMN chat_notifications BOOLEAN NOT NULL DEFAULT true;
        
        RAISE NOTICE 'Added chat_notifications column to push_notification_preferences table';
    ELSE
        RAISE NOTICE 'chat_notifications column already exists in push_notification_preferences table';
    END IF;
END $$;

COMMENT ON COLUMN public.push_notification_preferences.chat_notifications IS 'Enable/disable chat message notifications';

