-- Users profile table
CREATE TABLE users_profile (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    locale VARCHAR(5) DEFAULT 'nl-NL',
    regions TEXT[] DEFAULT '{}',
    topics TEXT[] DEFAULT '{}',
    artists TEXT[] DEFAULT '{}',
    teams TEXT[] DEFAULT '{}',
    notif_prefs JSONB DEFAULT '{"enabled": true, "digest": true}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sources table
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL CHECK (type IN ('news', 'music', 'events', 'sports')),
    name VARCHAR(100) NOT NULL,
    country VARCHAR(2) NOT NULL,
    lang VARCHAR(5) NOT NULL,
    url TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Items table
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('news', 'music', 'event', 'sport')),
    source_id INTEGER REFERENCES sources(id),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    lang VARCHAR(5) NOT NULL,
    summary_tr TEXT,
    summary_nl TEXT,
    tags TEXT[] DEFAULT '{}',
    regions TEXT[] DEFAULT '{}',
    quality_score DECIMAL(3,2) DEFAULT 0.5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(url)
);

-- Reactions table
CREATE TABLE reactions (
    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    emoji VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (item_id, user_id, emoji)
);

-- View for reaction counts
CREATE VIEW item_reaction_counts AS
SELECT 
    item_id,
    jsonb_object_agg(emoji, count) as counts
FROM (
    SELECT item_id, emoji, COUNT(*) as count
    FROM reactions
    GROUP BY item_id, emoji
) r
GROUP BY item_id;

-- Indexes for performance
CREATE INDEX idx_items_published_at ON items(published_at DESC);
CREATE INDEX idx_items_regions ON items USING GIN(regions);
CREATE INDEX idx_items_tags ON items USING GIN(tags);
CREATE INDEX idx_items_kind ON items(kind);

-- RLS Policies
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE reactions ENABLE ROW LEVEL SECURITY;

-- Users can only see/edit their own profile
CREATE POLICY "Users can view own profile" ON users_profile
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" ON users_profile
    FOR UPDATE USING (auth.uid() = user_id);

-- Anyone can view reactions, users can only add their own
CREATE POLICY "Anyone can view reactions" ON reactions
    FOR SELECT USING (true);

CREATE POLICY "Users can insert own reactions" ON reactions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Insert some initial sources
INSERT INTO sources (type, name, country, lang, url) VALUES
('news', 'NOS', 'NL', 'nl-NL', 'https://feeds.nos.nl/nieuws'),
('news', 'NU.nl', 'NL', 'nl-NL', 'https://www.nu.nl/rss'),
('news', 'TRT Haber', 'TR', 'tr-TR', 'https://www.trthaber.com/sondakika.rss'),
('news', 'Hürriyet', 'TR', 'tr-TR', 'https://www.hurriyet.com.tr/rss/anasayfa');
