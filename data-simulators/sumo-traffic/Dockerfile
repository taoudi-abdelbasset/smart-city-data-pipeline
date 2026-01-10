FROM python:3.11-slim

WORKDIR /app

# Install SUMO and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    wget \
    gnupg \
    procps && \
    wget -qO - https://sumo.dlr.de/sumo.gpg.key | apt-key add - && \
    add-apt-repository "deb https://sumo.dlr.de/apt jammy main" && \
    apt-get update && \
    apt-get install -y sumo sumo-tools && \
    rm -rf /var/lib/apt/lists/*

# Set SUMO_HOME
ENV SUMO_HOME=/usr/share/sumo
ENV PATH="${SUMO_HOME}/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY sumo_mqtt_connector.py .

# Run SUMO in headless mode with TraCI, then connector
CMD ["sh", "-c", "sumo -c /app/LuSTScenario/scenario/dua.actuated.sumocfg --remote-port 8813 & sleep 5 && python -u sumo_mqtt_connector.py"]
