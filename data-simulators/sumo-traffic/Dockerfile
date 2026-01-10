FROM ubuntu:22.04

WORKDIR /app

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install SUMO and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    wget \
    gnupg \
    procps \
    ca-certificates && \
    add-apt-repository ppa:sumo/stable && \
    apt-get update && \
    apt-get install -y sumo sumo-tools python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set SUMO_HOME
ENV SUMO_HOME=/usr/share/sumo
ENV PATH="${SUMO_HOME}/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY sumo_mqtt_connector.py .

# Run SUMO in headless mode with TraCI, then connector
CMD ["sh", "-c", "sumo -c /app/LuSTScenario/scenario/dua.actuated.sumocfg --remote-port 8813 & sleep 5 && python3 -u sumo_mqtt_connector.py"]
