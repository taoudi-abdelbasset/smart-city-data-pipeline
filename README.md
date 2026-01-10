# smart-city-data-pipeline

## simple-graphe-arch
```mermaid
graph TB
    subgraph "IoT DEVICES - Data Sources"
        A1[RTSP Cameras<br/>Vehicle/Pedestrian Detection]
        A2[SUMO Traffic<br/>Vehicle Telemetry]
        A3[Air Quality Sensors<br/>PM2.5, AQI]
        A4[Parking Sensors<br/>Occupancy via LoRaWAN]
    end
    
    subgraph "EDGE LAYER"
        B1[MQTT Broker<br/>Mosquitto]
        B2[RTSP Streams<br/>MediaMTX Server]
    end
    
    subgraph "INGESTION LAYER"
        C1[Apache Kafka<br/>Topics:<br/>- camera-data<br/>- traffic-data<br/>- air-quality<br/>- parking-data]
    end
    
    subgraph "STREAM PROCESSING"
        D1[Apache Flink<br/>Camera stream processing<br/>Real-time analytics]
        D2[Apache Spark Streaming<br/>MQTT data processing<br/>Congestion detection]
    end
    
    subgraph "LAKEHOUSE - Raw Data"
        F1[(HDFS / S3<br/>Unstructured raw data<br/>Parquet format<br/>- Camera frames<br/>- MQTT messages)]
    end
    
    subgraph "BATCH PROCESSING"
        E1[Apache Spark Batch<br/>- Structure data<br/>- Historical analysis<br/>- Daily reports]
        E2[Apache Airflow<br/>- Schedule jobs<br/>- Orchestrate ETL]
    end
    
    subgraph "DATA WAREHOUSE"
        F2[(PostgreSQL<br/>Structured data<br/>Aggregated analytics<br/>Query results)]
    end
    
    subgraph "REAL-TIME CACHE"
        F3[(Redis<br/>Real-time metrics<br/>Live dashboards)]
    end
    
    subgraph "ANALYTICS & ML"
        H1[Spark ML / TensorFlow<br/>- Traffic prediction<br/>- Anomaly detection<br/>- Pattern recognition]
    end
    
    subgraph "VISUALIZATION"
        J1[Grafana<br/>Real-time dashboards<br/>Live metrics]
        J2[Web Dashboard<br/>React/Flask<br/>Traffic maps<br/>Historical reports]
    end
    
    %% Data Flow - Ingestion
    A1 -->|RTSP Stream| B2
    A2 -->|MQTT| B1
    A3 -->|MQTT| B1
    A4 -->|MQTT| B1
    
    %% Edge to Kafka
    B1 -->|MQTT Messages| C1
    B2 -->|Camera Frames| C1
    
    %% Stream Processing
    C1 -->|Camera Topic| D1
    C1 -->|MQTT Topics| D2
    
    %% Stream to Lakehouse (Unstructured)
    D1 -.->|Raw camera data| F1
    D2 -.->|Raw MQTT data| F1
    
    %% Stream to Cache
    D1 -->|Real-time metrics| F3
    D2 -->|Real-time metrics| F3
    
    %% Batch Processing
    F1 -->|Raw data| E1
    E2 -.->|Schedule & Orchestrate| E1
    
    %% Batch to Data Warehouse (Structured)
    E1 -->|Structured data| F2
    
    %% Analytics & ML
    F2 -->|Structured data| H1
    H1 -->|Predictions & Insights| F2
    
    %% Visualization
    F3 -->|Live data| J1
    F2 -->|Historical data| J1
    F2 -->|Analytics| J2
    H1 -->|ML Insights| J2
    
    %% Styling
    style A1 fill:#ff6b6b
    style A2 fill:#ff6b6b
    style A3 fill:#ff6b6b
    style A4 fill:#ff6b6b
    style B1 fill:#4ecdc4
    style B2 fill:#4ecdc4
    style C1 fill:#45b7d1
    style D1 fill:#96ceb4
    style D2 fill:#96ceb4
    style E1 fill:#ffeaa7
    style E2 fill:#ffd93d
    style F1 fill:#a29bfe
    style F2 fill:#dfe6e9
    style F3 fill:#fab1a0
    style H1 fill:#fd79a8
    style J1 fill:#00b894
    style J2 fill:#00cec9
```
## full-prod-graphe-arch
```mermaid
graph TB
    subgraph "DATA SOURCES - IoT Layer"
        A1[RTSP Surveillance Cameras<br/>1000+ cameras citywide]
        A2[SUMO Traffic Simulator<br/>Vehicle telemetry]
        A3[Weather Stations<br/>Temperature, precipitation]
        A4[Air Quality Sensors<br/>PM2.5, AQI monitoring]
        A5[Parking IoT Sensors<br/>Occupancy detection]
    end

    subgraph "EDGE PROCESSING Layer"
        B1[Edge AI Server<br/>Computer Vision<br/>YOLO/TensorFlow]
        B2[IoT Gateway<br/>MQTT Broker Mosquitto<br/>Protocol Translation]
    end

    subgraph "INGESTION Layer - Message Queue"
        C1[Apache Kafka Cluster<br/>Topics:<br/>- camera-analytics<br/>- traffic-data<br/>- weather-data<br/>- air-quality<br/>- parking-data]
        C2[Schema Registry<br/>Avro/Protobuf schemas]
    end

    subgraph "STREAM PROCESSING - Real-Time"
        D1[Apache Flink<br/>- Camera stream processing<br/>- Complex event processing<br/>- Pattern detection]
        D2[Apache Spark Streaming<br/>- Traffic congestion detection<br/>- Real-time aggregations<br/>- MQTT data processing]
    end

    subgraph "LAKEHOUSE - Raw Unstructured Data"
        F1[(HDFS / S3 Data Lake<br/>Raw unstructured data<br/>Parquet format<br/>Partitioned by date/zone<br/>- Camera frames<br/>- MQTT messages<br/>- Sensor readings)]
        G1[Delta Lake / Apache Iceberg<br/>ACID transactions<br/>Schema evolution<br/>Time travel]
    end

    subgraph "BATCH PROCESSING - ETL"
        E1[Apache Spark Batch Jobs<br/>- Structure raw data<br/>- Daily traffic patterns<br/>- Weekly trend analysis<br/>- Data quality checks]
        E2[Apache Airflow<br/>- Job orchestration<br/>- Scheduled ETL<br/>- Pipeline monitoring]
    end

    subgraph "DATA WAREHOUSE - Structured Data"
        F3[(PostgreSQL/TimescaleDB<br/>Structured data<br/>Aggregated analytics<br/>Query results<br/>Historical reports)]
    end

    subgraph "REAL-TIME STORAGE"
        F2[(Apache Cassandra<br/>Time-series data<br/>High-throughput writes)]
        F4[(Redis Cache<br/>Latest sensor readings<br/>Real-time metrics)]
        F5[(Elasticsearch<br/>Full-text search<br/>Log aggregation)]
    end

    subgraph "ANALYTICS & ML Layer"
        H1[Apache Spark ML<br/>- Traffic prediction models<br/>- Congestion forecasting<br/>- Pattern analysis]
        H2[TensorFlow/PyTorch<br/>- Deep learning models<br/>- Computer vision training<br/>- Anomaly detection]
        H3[MLflow<br/>Model registry & tracking<br/>Model versioning]
    end

    subgraph "API & SERVICE Layer"
        I1[REST API Gateway<br/>FastAPI / Spring Boot<br/>Rate limiting]
        I2[GraphQL API<br/>Flexible data queries]
        I3[WebSocket Server<br/>Real-time updates<br/>Live dashboards]
    end

    subgraph "VISUALIZATION & MONITORING"
        J1[Grafana Dashboards<br/>Real-time metrics<br/>System health]
        J2[Apache Superset<br/>Business intelligence<br/>Custom reports]
        J3[Kibana<br/>Log analysis<br/>System logs]
        J4[Custom Web Dashboard<br/>React/Vue.js<br/>Traffic heatmaps<br/>ML insights]
    end

    subgraph "ALERTING & MONITORING"
        M1[Prometheus<br/>Metrics collection<br/>System monitoring]
        M2[AlertManager<br/>Alert routing<br/>Notification rules]
        M3[PagerDuty/Slack<br/>Incident notifications<br/>On-call alerts]
        M4[Custom Alert Engine<br/>Traffic threshold alerts<br/>Air quality warnings]
    end

    subgraph "SECURITY & GOVERNANCE"
        K1[Apache Ranger<br/>Access control & policies<br/>Data masking]
        K2[Apache Atlas<br/>Data lineage & catalog<br/>Metadata management]
        K3[HashiCorp Vault<br/>Secrets management<br/>API keys, credentials]
        K4[SSL/TLS Encryption<br/>Data in transit<br/>End-to-end encryption]
        K5[Encryption at Rest<br/>AES-256<br/>Storage encryption]
        K6[Keycloak/OAuth2<br/>Authentication<br/>Authorization]
    end

    subgraph "ORCHESTRATION & INFRASTRUCTURE"
        L1[Kubernetes<br/>Container orchestration<br/>Auto-scaling]
        L2[Docker<br/>Containerization<br/>Microservices]
        L3[Terraform<br/>Infrastructure as Code<br/>Multi-cloud deployment]
        L4[ELK Stack<br/>Centralized logging<br/>Logstash, Elasticsearch, Kibana]
    end

    %% Data Flow - Ingestion
    A1 -->|RTSP Stream| B1
    A2 -->|MQTT| B2
    A3 -->|MQTT| B2
    A4 -->|MQTT| B2
    A5 -->|MQTT| B2

    B1 -->|JSON Analytics| C1
    B2 -->|MQTT Messages| C1

    %% Schema validation
    C1 --> C2

    %% Stream Processing
    C2 -->|Camera topic| D1
    C2 -->|MQTT topics| D2

    %% Stream to Lakehouse (Unstructured)
    D1 -.->|Raw camera data| F1
    D2 -.->|Raw MQTT data| F1
    
    %% Stream to Real-time Storage
    D1 -->|Real-time metrics| F2
    D1 -->|Cache updates| F4
    D2 -->|Real-time metrics| F2
    D2 -->|Cache updates| F4

    %% Lakehouse layer
    F1 --> G1

    %% Batch Processing
    G1 -->|Raw data| E1
    E2 -.->|Orchestrates| E1

    %% Batch to Data Warehouse (Structured)
    E1 -->|Structured data| F3

    %% Analytics & ML
    F3 -->|Structured data| H1
    F3 -->|Training data| H2
    G1 -->|Historical data| H1
    H1 --> H3
    H2 --> H3
    H3 -->|Predictions| F3

    %% API Layer
    F2 -->|Time-series| I1
    F3 -->|Analytics| I1
    F4 -->|Cache| I1
    G1 -->|Lakehouse queries| I2
    I1 -->|Events| I3

    %% Visualization
    F4 -->|Live data| J1
    F3 -->|Historical data| J1
    I1 --> J2
    I2 --> J4
    I3 -->|Real-time| J4
    F5 --> J3
    H3 -->|ML Insights| J4

    %% Alerting & Monitoring
    M1 -->|Scrapes| D1
    M1 -->|Scrapes| D2
    M1 -->|Scrapes| E1
    M1 -->|Scrapes| L1
    M1 --> M2
    M2 --> M3
    D2 -.->|Traffic alerts| M4
    F3 -.->|Threshold checks| M4
    M4 --> M3

    %% Security & Governance
    K1 -.->|Governs| F1
    K1 -.->|Governs| F3
    K2 -.->|Catalogs| G1
    K3 -.->|Secures credentials| C1
    K3 -.->|Secures API keys| I1
    K4 -.->|Encrypts| B2
    K4 -.->|Encrypts| C1
    K5 -.->|Encrypts| F1
    K5 -.->|Encrypts| F3
    K6 -.->|Authenticates| I1

    %% Infrastructure
    L1 -.->|Deploys| D1
    L1 -.->|Deploys| D2
    L1 -.->|Deploys| E1
    L1 -.->|Deploys| I1
    L2 -.->|Packages| D1
    L2 -.->|Packages| I1
    L3 -.->|Provisions| L1
    L4 -.->|Logs| D1
    L4 -.->|Logs| E1
    L4 -.->|Logs| I1

    style A1 fill:#ff6b6b
    style B1 fill:#4ecdc4
    style C1 fill:#45b7d1
    style D1 fill:#96ceb4
    style D2 fill:#96ceb4
    style E1 fill:#ffeaa7
    style F1 fill:#a29bfe
    style G1 fill:#6c5ce7
    style F3 fill:#dfe6e9
    style F4 fill:#fab1a0
    style H1 fill:#fd79a8
    style H2 fill:#fd79a8
    style I1 fill:#fdcb6e
    style J1 fill:#00b894
    style K1 fill:#d63031
    style K6 fill:#e17055
    style L1 fill:#0984e3
    style M1 fill:#e84393
    style M3 fill:#ff7675
```