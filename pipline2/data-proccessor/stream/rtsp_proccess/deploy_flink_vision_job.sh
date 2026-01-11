#!/bin/bash
# Deploy Proper PyFlink Vision Job

set -e

echo "=========================================="
echo "🚀 Deploying PyFlink Vision Job"
echo "=========================================="

# Copy job file
echo "📋 Copying job file..."
cp flink_vision_job_proper.py ../../../flink-jobs/
chmod -R 777 flink-jobs/

# Rebuild Flink containers with updated Dockerfile
echo "🔨 Rebuilding Flink containers..."
docker-compose build flink-jobmanager flink-taskmanager

# Restart Flink
echo "🔄 Restarting Flink..."
docker-compose stop flink-jobmanager flink-taskmanager
docker-compose up -d flink-jobmanager flink-taskmanager

# Wait for Flink to be ready
echo "⏳ Waiting for Flink to be ready..."
sleep 10

# Check Flink health
if ! docker exec flink-jobmanager curl -f http://localhost:8081 > /dev/null 2>&1; then
    echo "❌ Flink is not healthy!"
    exit 1
fi

echo "✅ Flink is ready!"

# Submit job to Flink
echo ""
echo "=========================================="
echo "🎬 Submitting Job to Flink..."
echo "=========================================="
echo ""

# Run the PyFlink job
docker exec -d flink-jobmanager bash -c "
    cd /opt/flink-jobs &&
    nohup python3 flink_vision_job_proper.py > /tmp/vision_job.log 2>&1 &
"

sleep 3

# Check if job started
if docker exec flink-jobmanager pgrep -f "flink_vision_job_proper.py" > /dev/null; then
    PID=$(docker exec flink-jobmanager pgrep -f "flink_vision_job_proper.py")
    echo "✅ Job submitted successfully! (PID: $PID)"
    echo ""
    echo "🌐 Flink UI: http://localhost:8083"
    echo "   Look for: 'Vision Processor - Object Detection & Tracking'"
    echo ""
    echo "📋 View logs:"
    echo "   docker exec flink-jobmanager tail -f /tmp/vision_job.log"
    echo ""
    echo "🛑 Stop job:"
    echo "   docker exec flink-jobmanager pkill -f flink_vision_job_proper.py"
else
    echo "❌ Job failed to start!"
    echo "Check logs: docker exec flink-jobmanager cat /tmp/vision_job.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="