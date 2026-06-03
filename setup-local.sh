#!/bin/bash
# Setup script for Academic Content Generator - Local Deployment
# This script sets up everything needed to run the application locally

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║    Academic Content Generator - Local Setup                   ║"
echo "║         RAG + Multi-Agent + Human-in-the-Loop System           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed
check_docker() {
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker is installed"
        return 0
    else
        echo -e "${RED}✗${NC} Docker is not installed"
        echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
        exit 1
    fi
}

# Check if Docker Compose is installed
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker Compose is installed"
        return 0
    else
        echo -e "${RED}✗${NC} Docker Compose is not installed"
        exit 1
    fi
}

# Create .env file if it doesn't exist
setup_env() {
    if [ -f .env ]; then
        echo -e "${YELLOW}⚠${NC} .env file already exists"
        read -p "Do you want to reconfigure it? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    echo -e "${BLUE}Setting up .env file...${NC}"
    cp .env.example .env
    
    # Prompt for API keys
    read -p "Enter your Google API Key (or press Enter to skip): " google_key
    if [ -n "$google_key" ]; then
        sed -i.bak "s/your_google_api_key_here/$google_key/" .env && rm .env.bak
    fi
    
    read -p "Enter your OpenAI API Key (or press Enter to skip): " openai_key
    if [ -n "$openai_key" ]; then
        sed -i.bak "s/your_openai_api_key_here/$openai_key/" .env && rm .env.bak
    fi
    
    echo -e "${GREEN}✓${NC} .env file created"
}

# Build Docker images
build_images() {
    echo ""
    echo -e "${BLUE}Building Docker images...${NC}"
    docker-compose build
    echo -e "${GREEN}✓${NC} Docker images built"
}

# Start services
start_services() {
    echo ""
    echo -e "${BLUE}Starting services...${NC}"
    docker-compose up -d
    
    # Wait for services to be ready
    echo "Waiting for services to be ready..."
    sleep 5
    
    # Check backend health
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Backend is ready"
            break
        fi
        echo "Waiting for backend... (attempt $((attempt+1))/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}✗${NC} Backend failed to start"
        exit 1
    fi
}

# Initialize database
init_database() {
    echo ""
    echo -e "${BLUE}Initializing database...${NC}"
    
    # Run migrations or init script
    docker-compose exec -T backend python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
    
    echo -e "${GREEN}✓${NC} Database initialized"
}

# Print service URLs
print_urls() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}    Academic Content Generator is ready!                      ${GREEN}║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} Frontend:        ${BLUE}http://localhost:3000${NC}                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} Backend API:     ${BLUE}http://localhost:8000${NC}                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} API Docs:        ${BLUE}http://localhost:8000/docs${NC}                  ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} PostgreSQL:      ${BLUE}localhost:5432${NC}                             ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} Redis:           ${BLUE}localhost:6379${NC}                             ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} ChromaDB:        ${BLUE}http://localhost:8001${NC}                      ${GREEN}║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} Database Credentials:                                      ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   User: user                                               ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   Password: password                                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}   Database: academic_generator                             ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "To stop services: docker-compose down"
    echo "To view logs: docker-compose logs -f"
    echo "To stop and remove data: docker-compose down -v"
}

# Main setup flow
main() {
    echo ""
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    # Setup
    setup_env
    build_images
    start_services
    init_database
    
    # Display information
    print_urls
}

# Run main function
main
