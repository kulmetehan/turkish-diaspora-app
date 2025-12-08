-- 038_user_groups.sql
-- User groups infrastructure (EPIC-2.5)

CREATE TABLE IF NOT EXISTS public.user_groups (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    is_public BOOLEAN NOT NULL DEFAULT true,
    member_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_groups_name_length CHECK (LENGTH(name) >= 3 AND LENGTH(name) <= 100),
    CONSTRAINT user_groups_description_length CHECK (description IS NULL OR LENGTH(description) <= 500)
);

CREATE INDEX IF NOT EXISTS idx_user_groups_created_by ON public.user_groups(created_by);
CREATE INDEX IF NOT EXISTS idx_user_groups_public ON public.user_groups(is_public) WHERE is_public = true;
CREATE INDEX IF NOT EXISTS idx_user_groups_created_at ON public.user_groups(created_at DESC);

CREATE TABLE IF NOT EXISTS public.user_group_members (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES public.user_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member', -- 'owner', 'admin', 'member'
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(group_id, user_id),
    CONSTRAINT user_group_members_role_check CHECK (role IN ('owner', 'admin', 'member'))
);

CREATE INDEX IF NOT EXISTS idx_user_group_members_group ON public.user_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_user_group_members_user ON public.user_group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_user_group_members_role ON public.user_group_members(group_id, role);

-- Function to update member_count when members are added/removed
CREATE OR REPLACE FUNCTION update_group_member_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.user_groups
        SET member_count = member_count + 1,
            updated_at = now()
        WHERE id = NEW.group_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.user_groups
        SET member_count = GREATEST(0, member_count - 1),
            updated_at = now()
        WHERE id = OLD.group_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to maintain member_count
CREATE TRIGGER update_group_member_count_trigger
    AFTER INSERT OR DELETE ON public.user_group_members
    FOR EACH ROW
    EXECUTE FUNCTION update_group_member_count();

-- Automatically add creator as owner when group is created
CREATE OR REPLACE FUNCTION add_group_creator_as_owner()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_group_members (group_id, user_id, role, joined_at)
    VALUES (NEW.id, NEW.created_by, 'owner', now())
    ON CONFLICT (group_id, user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER add_group_creator_as_owner_trigger
    AFTER INSERT ON public.user_groups
    FOR EACH ROW
    EXECUTE FUNCTION add_group_creator_as_owner();

-- View for group activity (filters activity_stream by group members)
CREATE OR REPLACE VIEW public.user_group_activity AS
SELECT 
    g.id AS group_id,
    g.name AS group_name,
    a.id AS activity_id,
    a.actor_type,
    a.actor_id,
    a.activity_type,
    a.location_id,
    a.city_key,
    a.category_key,
    a.payload,
    a.created_at
FROM public.user_groups g
INNER JOIN public.user_group_members m ON m.group_id = g.id
INNER JOIN public.activity_stream a ON a.actor_id = m.user_id
ORDER BY a.created_at DESC;

COMMENT ON TABLE public.user_groups IS 'User-created groups for community organization';
COMMENT ON TABLE public.user_group_members IS 'Group membership and roles';
COMMENT ON VIEW public.user_group_activity IS 'Activity feed filtered by group membership';







