FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY air_quality_simulator.py .

# Run simulator
CMD ["python", "-u", "air_quality_simulator.py"]