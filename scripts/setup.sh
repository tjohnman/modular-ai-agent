#!/bin/bash

# Setup script for AI Agent System

echo "--- Initializing AI Agent System Setup ---"

# 1. Python Check
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# 2. Virtual Environment Setup
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate venv
source venv/bin/activate

# 3. Pip dependencies
echo "Installing/Updating pip dependencies..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found."
fi

# 4. Telegram Setup (Optional)
echo ""
read -p "Do you want to set up Telegram integration? (y/n): " telegram_choice
if [[ "$telegram_choice" == "y" || "$telegram_choice" == "Y" ]]; then
    echo "Starting Telegram setup..."
    python3 scripts/setup_telegram.py
else
    echo "Skipping Telegram setup."
fi

# 5. Environment File Check
echo ""
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo "⚠️  Please edit .env and fill in your configuration values."
    else
        echo "⚠️  Warning: .env.example not found. Please create a .env file manually."
    fi
else
    echo ".env file exists."
fi

# 6. Config File Check
if [ ! -f "config.json" ]; then
    echo "⚠️  Warning: config.json not found. Please create it before deployment."
fi

# 7. Docker Infrastructure
echo ""
echo "Checking Docker status..."
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo "Docker is running. Pulling required images..."
        docker pull python:3.11
    else
        echo "Warning: Docker is installed but not running. Please start Docker and run 'docker pull python:3.11' manually."
    fi
else
    echo "Warning: Docker is not installed. The 'python_analyser' tool will not function without Docker."
fi

echo ""
echo "--- Setup Complete! ---"

# 8. Deployment Prompt
echo ""
read -p "Do you want to deploy the application now? (y/n): " deploy_choice
if [[ "$deploy_choice" == "y" || "$deploy_choice" == "Y" ]]; then
    echo "Starting deployment..."
    ./scripts/deploy.sh
else
    echo "Deployment skipped. To deploy later, run: ./scripts/deploy.sh"
fi
