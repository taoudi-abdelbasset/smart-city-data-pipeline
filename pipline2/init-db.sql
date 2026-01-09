-- ============================================
-- SMART CITY ANALYTICS DATABASE SCHEMA
-- ============================================

-- Traffic Analytics Table
CREATE TABLE IF NOT EXISTS traffic_analytics (
    id SERIAL PRIMARY KEY,
    zone VARCHAR(100),
    road_id VARCHAR(100),
    road_type VARCHAR(50),
    avg_speed FLOAT,
    vehicle_count INTEGER,
    occupancy_rate FLOAT,
    congestion_level VARCHAR(20),
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_traffic_zone_time ON traffic_analytics(zone, timestamp);
CREATE INDEX idx_traffic_road_time ON traffic_analytics(road_id, timestamp);

-- Air Quality Analytics Table
CREATE TABLE IF NOT EXISTS air_quality_analytics (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(100),
    zone VARCHAR(100),
    pm25 FLOAT,
    pm10 FLOAT,
    no2 FLOAT,
    co FLOAT,
    o3 FLOAT,
    aqi INTEGER,
    aqi_category VARCHAR(50),
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_air_quality_zone_time ON air_quality_analytics(zone, timestamp);
CREATE INDEX idx_air_quality_sensor_time ON air_quality_analytics(sensor_id, timestamp);

-- Parking Analytics Table
CREATE TABLE IF NOT EXISTS parking_analytics (
    id SERIAL PRIMARY KEY,
    parking_lot_id VARCHAR(100),
    zone VARCHAR(100),
    total_spots INTEGER,
    occupied_spots INTEGER,
    available_spots INTEGER,
    occupancy_rate FLOAT,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parking_lot_time ON parking_analytics(parking_lot_id, timestamp);
CREATE INDEX idx_parking_zone_time ON parking_analytics(zone, timestamp);

-- Camera Events Table
CREATE TABLE IF NOT EXISTS camera_events (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(100),
    zone VARCHAR(100),
    event_type VARCHAR(50),
    vehicle_count INTEGER,
    pedestrian_count INTEGER,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_camera_zone_time ON camera_events(zone, timestamp);

-- Aggregated Hourly Traffic Stats
CREATE TABLE IF NOT EXISTS hourly_traffic_stats (
    id SERIAL PRIMARY KEY,
    zone VARCHAR(100),
    hour TIMESTAMP,
    total_vehicles INTEGER,
    avg_speed FLOAT,
    peak_congestion FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_hourly_stats_zone ON hourly_traffic_stats(zone, hour);

-- Real-time Dashboard Metrics (latest values)
CREATE TABLE IF NOT EXISTS realtime_metrics (
    metric_key VARCHAR(100) PRIMARY KEY,
    metric_value JSONB,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smartcity;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smartcity;