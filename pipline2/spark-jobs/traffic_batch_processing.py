#!/usr/bin/env python3
"""
Smart City Traffic Batch Processing
Reads raw traffic data from HDFS and generates analytics
Saves results to PostgreSQL
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, sum, window, current_timestamp
from datetime import datetime

def main():
    # Initialize Spark Session
    spark = SparkSession.builder \
        .appName("SmartCity_Traffic_Batch") \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.jars", "/opt/spark/jars/postgresql-42.6.0.jar") \
        .getOrCreate()
    
    print("=" * 80)
    print("SMART CITY TRAFFIC BATCH PROCESSING")
    print("=" * 80)
    
    # HDFS paths
    raw_data_path = "hdfs://namenode:9000/data/raw/traffic"
    processed_data_path = "hdfs://namenode:9000/data/processed/traffic"
    
    # PostgreSQL connection properties
    postgres_props = {
        "user": "smartcity",
        "password": "smartcity123",
        "driver": "org.postgresql.Driver",
        "url": "jdbc:postgresql://postgres:5432/smart_city_analytics"
    }
    
    try:
        # Read raw traffic data from HDFS (JSON format)
        print(f"\n📖 Reading data from: {raw_data_path}")
        
        df = spark.read \
            .option("multiline", "true") \
            .json(raw_data_path)
        
        print(f"✅ Loaded {df.count()} raw traffic events")
        df.printSchema()
        
        # Data cleaning and transformation
        print("\n🔧 Processing traffic data...")
        
        traffic_df = df.select(
            col("sensor_id"),
            col("road_id"),
            col("road_type"),
            col("zone"),
            col("vehicle_count").cast("int"),
            col("average_speed").cast("float"),
            col("occupancy_rate").cast("float"),
            col("event_time").cast("timestamp").alias("timestamp")
        )
        
        # Calculate congestion level
        from pyspark.sql.functions import when
        
        traffic_df = traffic_df.withColumn(
            "congestion_level",
            when(col("occupancy_rate") > 0.8, "high")
            .when(col("occupancy_rate") > 0.5, "medium")
            .otherwise("low")
        )
        
        # Aggregate by zone
        print("\n📊 Calculating zone-level analytics...")
        
        zone_analytics = traffic_df.groupBy("zone", "timestamp") \
            .agg(
                avg("average_speed").alias("avg_speed"),
                sum("vehicle_count").alias("total_vehicles"),
                avg("occupancy_rate").alias("avg_occupancy")
            )
        
        print("\n📊 Zone Analytics Sample:")
        zone_analytics.show(10)
        
        # Aggregate by road type
        print("\n📊 Calculating road type analytics...")
        
        road_analytics = traffic_df.groupBy("road_type", "timestamp") \
            .agg(
                avg("average_speed").alias("avg_speed"),
                count("*").alias("event_count"),
                avg("occupancy_rate").alias("avg_occupancy")
            )
        
        print("\n📊 Road Type Analytics Sample:")
        road_analytics.show(10)
        
        # Save processed data to HDFS (Parquet format)
        print(f"\n💾 Saving processed data to: {processed_data_path}")
        
        traffic_df.write \
            .mode("append") \
            .partitionBy("zone") \
            .parquet(f"{processed_data_path}/traffic_events")
        
        print("✅ Data saved to HDFS in Parquet format")
        
        # Save analytics to PostgreSQL
        print("\n💾 Saving analytics to PostgreSQL...")
        
        # Prepare data for PostgreSQL (add created_at timestamp)
        traffic_for_db = traffic_df.select(
            "zone", "road_id", "road_type", "avg_speed", 
            "vehicle_count", "occupancy_rate", "congestion_level", "timestamp"
        ).withColumn("created_at", current_timestamp())
        
        # Write to PostgreSQL
        traffic_for_db.write \
            .jdbc(
                url=postgres_props["url"],
                table="traffic_analytics",
                mode="append",
                properties=postgres_props
            )
        
        print("✅ Analytics saved to PostgreSQL (traffic_analytics table)")
        
        # Generate summary statistics
        print("\n" + "=" * 80)
        print("PROCESSING SUMMARY")
        print("=" * 80)
        print(f"Total events processed: {df.count()}")
        print(f"Unique zones: {traffic_df.select('zone').distinct().count()}")
        print(f"Unique roads: {traffic_df.select('road_id').distinct().count()}")
        print(f"Time range: {traffic_df.agg({'timestamp': 'min'}).collect()[0][0]} to {traffic_df.agg({'timestamp': 'max'}).collect()[0][0]}")
        print("=" * 80)
        
        print("\n✅ Batch processing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during batch processing: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()