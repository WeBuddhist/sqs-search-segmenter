#!/bin/bash

# Quick Start Script for Celery Microservice
# This script helps you get the application up and running quickly

set -e  # Exit on error

echo "🚀 Celery Microservice - Quick Start"
echo "===================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from env.example..."
    cp env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your actual credentials before continuing!"
    echo ""
    read -p "Press enter to continue after editing .env..."
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

echo ""
echo "✅ Docker and docker-compose are installed"
echo ""

# Ask user what they want to do
echo "What would you like to do?"
echo "1) Build and start the application"
echo "2) Stop the application"
echo "3) View logs"
echo "4) Rebuild from scratch"
echo "5) Exit"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🏗️  Building and starting the application..."
        docker-compose up --build -d
        echo ""
        echo "✅ Application started successfully!"
        echo ""
        echo "📊 Service Status:"
        docker-compose ps
        echo ""
        echo "🌐 Application is running at: http://localhost:8080"
        echo "📊 Health check: http://localhost:8080/health"
        echo ""
        echo "To view logs, run: docker-compose logs -f web"
        ;;
    2)
        echo ""
        echo "🛑 Stopping the application..."
        docker-compose down
        echo "✅ Application stopped"
        ;;
    3)
        echo ""
        echo "📋 Viewing logs (Press Ctrl+C to exit)..."
        docker-compose logs -f web
        ;;
    4)
        echo ""
        echo "🔄 Rebuilding from scratch..."
        docker-compose down -v
        docker-compose build --no-cache
        docker-compose up -d
        echo ""
        echo "✅ Application rebuilt and started!"
        echo "🌐 Application is running at: http://localhost:8080"
        ;;
    5)
        echo ""
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

