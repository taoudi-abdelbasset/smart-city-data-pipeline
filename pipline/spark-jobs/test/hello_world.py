"""
Simple Spark Job - Hello World to HDFS
This job creates sample data and saves it to HDFS
"""
from pyspark.sql import SparkSession
from datetime import datetime

def main():
    # Create Spark session
    spark = SparkSession.builder \
        .appName("HelloWorld-HDFS") \
        .master("spark://spark-master:7077") \
        .getOrCreate()
    
    print("=" * 50)
    print("🚀 Spark Hello World Job Started!")
    print("=" * 50)
    
    # Create sample data
    data = [
        ("Hello from Spark!", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Writing to HDFS", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Smart City Pipeline", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Test successful!", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ]
    
    # Create DataFrame
    df = spark.createDataFrame(data, ["message", "timestamp"])
    
    print("\n📊 Sample Data:")
    df.show(truncate=False)
    
    # Write to HDFS
    hdfs_path = "hdfs://namenode:8020/smartcity/test/hello_world"
    print(f"\n💾 Writing to HDFS: {hdfs_path}")
    
    df.write.mode("overwrite").parquet(hdfs_path)
    
    print("\n✅ Data written successfully!")
    
    # Read back to verify
    print("\n🔍 Reading back from HDFS to verify...")
    df_read = spark.read.parquet(hdfs_path)
    df_read.show(truncate=False)
    
    print("\n" + "=" * 50)
    print("✨ Job completed successfully!")
    print("=" * 50)
    
    spark.stop()

if __name__ == "__main__":
    main()