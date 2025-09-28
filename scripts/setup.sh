#!/bin/bash

echo "Setting up Museum AI Companion..."

# Create necessary directories
mkdir -p logs
mkdir -p data
mkdir -p cache

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

# Install Python dependencies for each service
echo "Installing dependencies..."
for service in chatbot cv localization edge; do
    if [ -d "$service" ] && [ -f "$service/requirements.txt" ]; then
        echo "Installing dependencies for $service..."
        pip install -r "$service/requirements.txt"
    fi
done

# Build Docker images
echo "Building Docker images..."
docker-compose build

# Initialize databases
echo "Initializing databases..."
docker-compose up -d postgres
sleep 10  # Wait for PostgreSQL to start

echo "Setup complete! Run 'make up' to start all services."