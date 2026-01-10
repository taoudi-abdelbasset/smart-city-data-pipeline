FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY parking_simulator.py .

# Run simulator
CMD ["python", "-u", "parking_simulator.py"]