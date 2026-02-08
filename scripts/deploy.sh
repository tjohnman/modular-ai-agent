#!/bin/bash

# Deployment script for AI Agent System

# 1. Build and start/restart the service
# Ensure we are in the project root
if [ -d "deploy" ]; then
    # We are likely in root
    PROJECT_ROOT="."
elif [ -d "../deploy" ]; then
    # We are likely in scripts/
    PROJECT_ROOT=".."
else
    echo "Error: Could not locate project root."
    exit 1
fi

cd "$PROJECT_ROOT"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found in project root ($PWD)."
    exit 1
fi

# Detect Timezone
if [ -f /etc/timezone ]; then
    TZ=$(cat /etc/timezone)
elif [ -L /etc/localtime ]; then
    TZ=$(readlink /etc/localtime | sed 's#/var/db/timezone/zoneinfo/##')
else
    TZ="UTC"
fi
export TZ
echo "Detected Timezone: $TZ"

# 1. Build and start/restart the service
echo "Updating service from $PWD..."
docker compose --env-file .env -f deploy/docker-compose.yml up -d --build

echo "Deployment complete! Service is running in the background."
echo "Use 'docker logs -f agent-system' to view logs."
