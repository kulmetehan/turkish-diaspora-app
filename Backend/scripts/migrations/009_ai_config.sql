-- Create ai_config table for centralized AI threshold and policy management
-- This table uses a single-row pattern with a constant ID to enforce singleton behavior

CREATE TABLE IF NOT EXISTS ai_config (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    classify_min_conf FLOAT NOT NULL DEFAULT 0.80,
    verify_min_conf FLOAT NOT NULL DEFAULT 0.80,
    task_verifier_min_conf FLOAT NOT NULL DEFAULT 0.80,
    auto_promote_conf FLOAT NOT NULL DEFAULT 0.90,
    monitor_low_conf_days INTEGER NOT NULL DEFAULT 3,
    monitor_medium_conf_days INTEGER NOT NULL DEFAULT 7,
    monitor_high_conf_days INTEGER NOT NULL DEFAULT 14,
    monitor_verified_few_reviews_days INTEGER NOT NULL DEFAULT 30,
    monitor_verified_medium_reviews_days INTEGER NOT NULL DEFAULT 60,
    monitor_verified_many_reviews_days INTEGER NOT NULL DEFAULT 90,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by TEXT
);

-- Add constraints to ensure valid ranges
ALTER TABLE ai_config
    ADD CONSTRAINT ai_config_classify_min_conf_range CHECK (classify_min_conf >= 0.0 AND classify_min_conf <= 1.0),
    ADD CONSTRAINT ai_config_verify_min_conf_range CHECK (verify_min_conf >= 0.0 AND verify_min_conf <= 1.0),
    ADD CONSTRAINT ai_config_task_verifier_min_conf_range CHECK (task_verifier_min_conf >= 0.0 AND task_verifier_min_conf <= 1.0),
    ADD CONSTRAINT ai_config_auto_promote_conf_range CHECK (auto_promote_conf >= 0.0 AND auto_promote_conf <= 1.0),
    ADD CONSTRAINT ai_config_monitor_low_conf_days_min CHECK (monitor_low_conf_days >= 1),
    ADD CONSTRAINT ai_config_monitor_medium_conf_days_min CHECK (monitor_medium_conf_days >= 1),
    ADD CONSTRAINT ai_config_monitor_high_conf_days_min CHECK (monitor_high_conf_days >= 1),
    ADD CONSTRAINT ai_config_monitor_verified_few_reviews_days_min CHECK (monitor_verified_few_reviews_days >= 1),
    ADD CONSTRAINT ai_config_monitor_verified_medium_reviews_days_min CHECK (monitor_verified_medium_reviews_days >= 1),
    ADD CONSTRAINT ai_config_monitor_verified_many_reviews_days_min CHECK (monitor_verified_many_reviews_days >= 1);

-- Initialize with default values if table is empty
INSERT INTO ai_config (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- Add comment to explain the table purpose
COMMENT ON TABLE ai_config IS 'Centralized AI policy configuration: confidence thresholds and freshness policy intervals. Single-row table (id=1 enforced).';
COMMENT ON COLUMN ai_config.classify_min_conf IS 'Minimum confidence for classify_bot to apply classification (0.0-1.0)';
COMMENT ON COLUMN ai_config.verify_min_conf IS 'Minimum confidence for verify_locations bot to promote to VERIFIED (0.0-1.0)';
COMMENT ON COLUMN ai_config.task_verifier_min_conf IS 'Minimum confidence for task_verifier bot (0.0-1.0)';
COMMENT ON COLUMN ai_config.auto_promote_conf IS 'Auto-promotion threshold for task_verifier (high confidence + Turkish cues) (0.0-1.0)';
COMMENT ON COLUMN ai_config.monitor_low_conf_days IS 'Freshness interval (days) for low confidence locations (< 0.60)';
COMMENT ON COLUMN ai_config.monitor_medium_conf_days IS 'Freshness interval (days) for medium confidence locations (0.60-0.80)';
COMMENT ON COLUMN ai_config.monitor_high_conf_days IS 'Freshness interval (days) for high confidence locations (>= 0.80)';
COMMENT ON COLUMN ai_config.monitor_verified_few_reviews_days IS 'Freshness interval (days) for VERIFIED locations with < 10 reviews';
COMMENT ON COLUMN ai_config.monitor_verified_medium_reviews_days IS 'Freshness interval (days) for VERIFIED locations with 10-99 reviews';
COMMENT ON COLUMN ai_config.monitor_verified_many_reviews_days IS 'Freshness interval (days) for VERIFIED locations with >= 100 reviews';



