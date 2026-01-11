-- Initialize TimescaleDB for Smart City Real-Time Analytics
-- This creates hypertables for time-series data

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Vision Analytics - Object Detections
CREATE TABLE IF NOT EXISTS vision_detections (
    time TIMESTAMPTZ NOT NULL,
    camera_id VARCHAR(50) NOT NULL,
    object_id INTEGER NOT NULL,
    object_type VARCHAR(20) NOT NULL,
    bbox_x1 INTEGER,
    bbox_y1 INTEGER,
    bbox_x2 INTEGER,
    bbox_y2 INTEGER,
    centroid_x INTEGER,
    centroid_y INTEGER,
    tracking_duration FLOAT,
    gender VARCHAR(20),
    gender_confidence FLOAT,
    age VARCHAR(20),
    age_confidence FLOAT
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable('vision_detections', 'time', if_not_exists => TRUE);

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_camera_time ON vision_detections (camera_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_object_type ON vision_detections (object_type, time DESC);

-- Traffic Analytics - Aggregated Counts
CREATE TABLE IF NOT EXISTS traffic_counts (
    time TIMESTAMPTZ NOT NULL,
    camera_id VARCHAR(50) NOT NULL,
    total_persons INTEGER DEFAULT 0,
    total_cars INTEGER DEFAULT 0,
    avg_tracking_duration FLOAT,
    male_count INTEGER DEFAULT 0,
    female_count INTEGER DEFAULT 0,
    children_count INTEGER DEFAULT 0,
    adults_count INTEGER DEFAULT 0
);

-- Convert to hypertable
SELECT create_hypertable('traffic_counts', 'time', if_not_exists => TRUE);

-- Create continuous aggregates for 1-minute summaries
CREATE MATERIALIZED VIEW IF NOT EXISTS traffic_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    camera_id,
    COUNT(*) AS total_detections,
    COUNT(DISTINCT object_id) AS unique_objects,
    AVG(tracking_duration) AS avg_duration
FROM vision_detections
GROUP BY bucket, camera_id
WITH NO DATA;

-- Refresh policy (auto-update every minute)
SELECT add_continuous_aggregate_policy('traffic_1min',
    start_offset => INTERVAL '3 minutes',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE
);

-- Data retention policy (keep 7 days)
SELECT add_retention_policy('vision_detections', 
    INTERVAL '7 days',
    if_not_exists => TRUE
);

COMMENT ON TABLE vision_detections IS 'Real-time object detection data from Flink stream processing';
COMMENT ON TABLE traffic_counts IS 'Aggregated traffic statistics per camera';