-- 104_chat_forum.sql
-- Chat/Forum infrastructure for content-based chat topics

-- Chat Topics (één per content item)
CREATE TABLE IF NOT EXISTS public.chat_topics (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL, -- 'feed', 'news', 'event', 'music'
    content_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_count INTEGER NOT NULL DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    UNIQUE(content_type, content_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_topics_content ON public.chat_topics(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_chat_topics_updated ON public.chat_topics(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_topics_active ON public.chat_topics(is_active) WHERE is_active = TRUE;

-- Chat Messages
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES public.chat_topics(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_message_id INTEGER REFERENCES public.chat_messages(id) ON DELETE SET NULL,
    quoted_message_id INTEGER REFERENCES public.chat_messages(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_topic_created ON public.chat_messages(topic_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON public.chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_parent ON public.chat_messages(parent_message_id) WHERE parent_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chat_messages_quoted ON public.chat_messages(quoted_message_id) WHERE quoted_message_id IS NOT NULL;

-- Chat Topic Subscriptions (voor last_read tracking en notificaties)
CREATE TABLE IF NOT EXISTS public.chat_topic_subscriptions (
    topic_id INTEGER NOT NULL REFERENCES public.chat_topics(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    last_read_at TIMESTAMPTZ,
    last_read_message_id INTEGER REFERENCES public.chat_messages(id),
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notification_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    
    PRIMARY KEY (topic_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_topic_subscriptions_user_topics ON public.chat_topic_subscriptions(user_id, last_read_at DESC);

-- Chat Message Reactions
CREATE TABLE IF NOT EXISTS public.chat_message_reactions (
    message_id INTEGER NOT NULL REFERENCES public.chat_messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    emoji VARCHAR(10) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (message_id, user_id, emoji)
);

CREATE INDEX IF NOT EXISTS idx_chat_message_reactions_message ON public.chat_message_reactions(message_id, emoji);

-- Functions & Triggers voor message_count en last_message_at updates
CREATE OR REPLACE FUNCTION update_chat_topic_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.chat_topics
    SET 
        message_count = (
            SELECT COUNT(*) 
            FROM public.chat_messages 
            WHERE topic_id = NEW.topic_id AND is_deleted = FALSE
        ),
        last_message_at = NEW.created_at,
        updated_at = NOW()
    WHERE id = NEW.topic_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chat_message_insert_trigger ON public.chat_messages;
CREATE TRIGGER chat_message_insert_trigger
AFTER INSERT ON public.chat_messages
FOR EACH ROW
WHEN (NEW.is_deleted = FALSE)
EXECUTE FUNCTION update_chat_topic_stats();

-- Update trigger voor wanneer message wordt soft-deleted
CREATE OR REPLACE FUNCTION update_chat_topic_stats_on_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.chat_topics
    SET 
        message_count = (
            SELECT COUNT(*) 
            FROM public.chat_messages 
            WHERE topic_id = OLD.topic_id AND is_deleted = FALSE
        ),
        updated_at = NOW()
    WHERE id = OLD.topic_id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chat_message_update_trigger ON public.chat_messages;
CREATE TRIGGER chat_message_update_trigger
AFTER UPDATE OF is_deleted ON public.chat_messages
FOR EACH ROW
WHEN (OLD.is_deleted != NEW.is_deleted)
EXECUTE FUNCTION update_chat_topic_stats_on_delete();

-- Enable Realtime voor chat_messages en chat_topics (Supabase Realtime)
-- Note: This requires Supabase Realtime to be enabled in the dashboard
DO $$
BEGIN
    -- Add to realtime publication if not already added
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' 
        AND tablename = 'chat_messages'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_messages;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' 
        AND tablename = 'chat_topics'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_topics;
    END IF;
END $$;

COMMENT ON TABLE public.chat_topics IS 'Chat topics linked to content items (feed, news, events, music)';
COMMENT ON TABLE public.chat_messages IS 'Chat messages within topics with support for replies and quotes';
COMMENT ON TABLE public.chat_topic_subscriptions IS 'User subscriptions to topics for notification and read tracking';
COMMENT ON TABLE public.chat_message_reactions IS 'Emoji reactions on chat messages';





