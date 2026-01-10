.PHONY: help build up down restart logs clean status

help: ## Show this help message
	@echo "Smart City Data Simulators - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup: ## Create necessary directories
	@echo "Creating directories..."
	@mkdir -p mosquitto/config mosquitto/data mosquitto/log
	@echo "✅ Setup complete"

build: setup ## Build all Docker images
	@echo "Building all services..."
	docker-compose build
	@echo "✅ Build complete"

up: ## Start all services
	@echo "Starting all services..."
	docker-compose up -d
	@echo "✅ All services started"
	@make status

up-with-kafka: ## Start all services including Kafka bridge
	@echo "Starting all services with Kafka bridge..."
	docker-compose --profile with-kafka up -d
	@echo "✅ All services started"

down: ## Stop all services
	@echo "Stopping all services..."
	docker-compose down
	@echo "✅ All services stopped"

restart: ## Restart all services
	@echo "Restarting all services..."
	docker-compose restart
	@echo "✅ All services restarted"

restart-air: ## Restart air quality service
	docker-compose restart air-quality

restart-parking: ## Restart parking service
	docker-compose restart parking-sensors

restart-camera: ## Restart camera service
	docker-compose restart camera-simulator

restart-sumo: ## Restart SUMO service
	docker-compose restart sumo-traffic

logs: ## Show logs from all services
	docker-compose logs -f

logs-air: ## Show air quality logs
	docker-compose logs -f air-quality

logs-parking: ## Show parking logs
	docker-compose logs -f parking-sensors

logs-camera: ## Show camera logs
	docker-compose logs -f camera-simulator

logs-sumo: ## Show SUMO logs
	docker-compose logs -f sumo-traffic

logs-mqtt: ## Show MQTT broker logs
	docker-compose logs -f mosquitto

status: ## Show status of all services
	@echo ""
	@echo "==================================================================="
	@echo "📊 Smart City Services Status"
	@echo "==================================================================="
	@docker-compose ps
	@echo ""
	@echo "🔍 Quick Health Check:"
	@echo ""
	@docker ps --filter "name=smart-city" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

clean: ## Remove all containers, images, and volumes
	@echo "⚠️  This will remove all containers, images, and volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		rm -rf mosquitto/data/* mosquitto/log/*; \
		echo "✅ Cleanup complete"; \
	fi

test-mqtt: ## Test MQTT connection
	@echo "Testing MQTT broker..."
	@docker exec smart-city-mosquitto mosquitto_sub -t '$$SYS/#' -C 1

monitor-mqtt: ## Monitor all MQTT messages
	@echo "Monitoring all MQTT topics (Ctrl+C to stop)..."
	@docker exec -it smart-city-mosquitto mosquitto_sub -v -t '#'

monitor-parking: ## Monitor parking MQTT messages
	@echo "Monitoring parking topics (Ctrl+C to stop)..."
	@docker exec -it smart-city-mosquitto mosquitto_sub -v -t 'parking/#'

monitor-air: ## Monitor air quality MQTT messages
	@echo "Monitoring air quality topics (Ctrl+C to stop)..."
	@docker exec -it smart-city-mosquitto mosquitto_sub -v -t 'air_quality/#'

monitor-sumo: ## Monitor SUMO traffic MQTT messages
	@echo "Monitoring SUMO traffic topics (Ctrl+C to stop)..."
	@docker exec -it smart-city-mosquitto mosquitto_sub -v -t 'traffic/#'

shell-air: ## Open shell in air quality container
	docker-compose exec air-quality /bin/bash

shell-parking: ## Open shell in parking container
	docker-compose exec parking-sensors /bin/bash

shell-camera: ## Open shell in camera container
	docker-compose exec camera-simulator /bin/bash

shell-sumo: ## Open shell in SUMO container
	docker-compose exec sumo-traffic /bin/bash