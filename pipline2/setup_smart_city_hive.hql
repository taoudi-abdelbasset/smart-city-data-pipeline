-- ====================================================================
-- SMART CITY HIVE SCHEMA BACKUP
-- Run this to recreate all tables and link to HDFS data
-- ====================================================================

-- 1. VISION DETECTIONS (From Flink)
CREATE EXTERNAL TABLE IF NOT EXISTS vision_detections (
    camera_id STRING,
    `timestamp` STRING,
    total_objects INT,
    detections ARRAY<STRUCT<
        object_id: INT,
        `type`: STRING,
        bounding_box: STRUCT<x1:INT, y1:INT, x2:INT, y2:INT>,
        centroid: STRUCT<x:INT, y:INT>,
        tracking_duration_seconds: DOUBLE,
        gender: STRING,
        gender_confidence: DOUBLE,
        age: STRING,
        age_confidence: DOUBLE
    >>
)
PARTITIONED BY (year INT, month INT, day INT)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:8020/smart-city/vision-detections';

-- 2. AIR QUALITY
CREATE EXTERNAL TABLE IF NOT EXISTS air_quality (
    mqtt_topic STRING,
    `timestamp` STRING,
    bridge_received_at STRING,
    data STRUCT<
        device_type:STRING,
        protocol:STRING,
        sensor_id:STRING,
        sensor_name:STRING,
        `timestamp`:STRING,
        location:STRUCT<gps:STRUCT<latitude:DOUBLE,longitude:DOUBLE>,city:STRING,zone:STRING,address:STRING>,
        measurements:STRUCT<pm25:DOUBLE,pm10:DOUBLE,no2:DOUBLE,co:DOUBLE,o3:DOUBLE,so2:DOUBLE,temperature_celsius:DOUBLE,humidity_percent:DOUBLE>,
        aqi:STRUCT<value:INT,category:STRING,health_advisory:STRING>,
        sensor_status:STRUCT<online:BOOLEAN,calibration_date:STRING,battery_percent:INT,signal_strength:INT>
    >
)
PARTITIONED BY (year INT, month INT, day INT, hour INT)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:8020/smart-city/air-quality';

-- 3. PARKING
CREATE EXTERNAL TABLE IF NOT EXISTS parking (
    mqtt_topic STRING,
    `timestamp` STRING,
    bridge_received_at STRING,
    data STRUCT<
        device_type:STRING,
        protocol:STRING,
        parking_lot_id:STRING,
        parking_lot_name:STRING,
        `timestamp`:STRING,
        location:STRUCT<gps:STRUCT<latitude:DOUBLE,longitude:DOUBLE>,city:STRING,zone:STRING,address:STRING>,
        occupancy:STRUCT<total_spots:INT,occupied_spots:INT,available_spots:INT,occupancy_rate:DOUBLE,status:STRING>,
        vehicle_breakdown:MAP<STRING,INT>,
        pricing:STRUCT<current_rate_per_hour:DOUBLE,currency:STRING>,
        sensor_status:STRUCT<online_sensors:INT,offline_sensors:INT,battery_low:INT>,
        event:STRUCT<event_type:STRING,spot_id:STRING,vehicle_type:STRING,license_plate:STRING,`timestamp`:STRING,duration_minutes:DOUBLE>
    >
)
PARTITIONED BY (year INT, month INT, day INT, hour INT)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:8020/smart-city/parking';

-- 4. TRAFFIC EDGES
-- 1. CORRECTED TRAFFIC EDGES
DROP TABLE IF EXISTS traffic_edges;
CREATE EXTERNAL TABLE traffic_edges (
    mqtt_topic STRING,
    `timestamp` STRING,
    bridge_received_at STRING,
    data STRUCT<
        device_type:STRING,
        edge_id:STRING,
        `timestamp`:STRING,
        simulation_time:DOUBLE,
        traffic_data:STRUCT<
            vehicle_count:INT,
            average_speed_kmh:DOUBLE,
            lane_occupancy:DOUBLE,
            congestion_level:STRING,
            vehicle_types:MAP<STRING,INT>
        >
    >
)
PARTITIONED BY (year INT, month INT, day INT, hour INT)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:8020/smart-city/traffic/edges';

-- 5. TRAFFIC VEHICLES


-- 2. CORRECTED TRAFFIC VEHICLES
DROP TABLE IF EXISTS traffic_vehicles;
CREATE EXTERNAL TABLE traffic_vehicles (
    mqtt_topic STRING,
    `timestamp` STRING,
    bridge_received_at STRING,
    data STRUCT<
        vehicle_id:STRING,
        `timestamp`:STRING,
        simulation_time:DOUBLE,
        vehicle_info:STRUCT<type:STRING, vehicle_class:STRING>,
        location:STRUCT<
            position:STRUCT<x:DOUBLE, y:DOUBLE>,
            road_id:STRING,
            lane_id:STRING
        >,
        dynamics:STRUCT<speed_kmh:DOUBLE, acceleration:DOUBLE>,
        emissions:STRUCT<co2_mg_s:DOUBLE, fuel_ml_s:DOUBLE>,
        traffic_state:STRUCT<waiting_time_s:DOUBLE>
    >
)
PARTITIONED BY (year INT, month INT, day INT, hour INT)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:8020/smart-city/traffic/vehicles';

-- 6. TRAFFIC LIGHTS
DROP TABLE IF EXISTS traffic_lights;
CREATE EXTERNAL TABLE traffic_lights (
    mqtt_topic STRING,
    `timestamp` STRING,
    bridge_received_at STRING,
    data STRUCT<
        `timestamp`:STRING,
        traffic_light_id:STRING,
        state:STRING,
        phase_duration:INT,
        next_switch:INT
    >
)
PARTITIONED BY (year INT, month INT, day INT, hour INT)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:8020/smart-city/traffic/traffic_lights';

-- 7. SIMULATION STATS
-- 3. CORRECTED SIMULATION STATS
DROP TABLE IF EXISTS simulation_stats;
CREATE EXTERNAL TABLE simulation_stats (
    mqtt_topic STRING,
    `timestamp` STRING,
    bridge_received_at STRING,
    data STRUCT<
        `timestamp`:STRING,
        simulation_time:DOUBLE,
        statistics:STRUCT<
            vehicles_departed:INT,
            vehicles_arrived:INT,
            vehicles_current:INT,
            vehicles_loaded:INT
        >
    >
)
PARTITIONED BY (year INT, month INT, day INT, hour INT)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:8020/smart-city/traffic/simulation_stats';

-- ====================================================================
-- REFRESH METADATA (Discovery of HDFS folders)
-- ====================================================================
MSCK REPAIR TABLE vision_detections;
MSCK REPAIR TABLE air_quality;
MSCK REPAIR TABLE parking;
MSCK REPAIR TABLE traffic_edges;
MSCK REPAIR TABLE traffic_vehicles;
MSCK REPAIR TABLE traffic_lights;
MSCK REPAIR TABLE simulation_stats;