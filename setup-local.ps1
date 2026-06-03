# Setup script for Academic Content Generator - Local Deployment (Windows)
# This script sets up everything needed to run the application locally on Windows

param(
    [switch]$SkipDocker = $false,
    [switch]$SkipBuild = $false
)

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║    Academic Content Generator - Local Setup (Windows)         ║" -ForegroundColor Green
Write-Host "║         RAG + Multi-Agent + Human-in-the-Loop System           ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Check if Docker is installed
function Test-Docker {
    try {
        $version = docker --version
        Write-Host "✓ Docker is installed: $version" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ Docker is not installed" -ForegroundColor Red
        Write-Host "Please install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        return $false
    }
}

# Check if Docker Compose is installed
function Test-DockerCompose {
    try {
        $version = docker-compose --version
        Write-Host "✓ Docker Compose is installed: $version" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ Docker Compose is not installed" -ForegroundColor Red
        return $false
    }
}

# Setup .env file
function Initialize-Env {
    if ((Test-Path ".env") -and -not $SkipDocker) {
        Write-Host "⚠ .env file already exists" -ForegroundColor Yellow
        $response = Read-Host "Do you want to reconfigure it? (y/n)"
        if ($response -ne "y" -and $response -ne "Y") {
            return
        }
    }
    
    Write-Host "Setting up .env file..." -ForegroundColor Blue
    Copy-Item ".env.example" ".env" -Force
    
    # Prompt for API keys
    $googleKey = Read-Host "Enter your Google API Key (or press Enter to skip)"
    if ($googleKey) {
        (Get-Content ".env") -replace "your_google_api_key_here", $googleKey | Set-Content ".env"
    }
    
    $openaiKey = Read-Host "Enter your OpenAI API Key (or press Enter to skip)"
    if ($openaiKey) {
        (Get-Content ".env") -replace "your_openai_api_key_here", $openaiKey | Set-Content ".env"
    }
    
    Write-Host "✓ .env file created" -ForegroundColor Green
}

# Build Docker images
function Invoke-Build {
    Write-Host ""
    Write-Host "Building Docker images..." -ForegroundColor Blue
    docker-compose build
    Write-Host "✓ Docker images built" -ForegroundColor Green
}

# Start services
function Start-Services {
    Write-Host ""
    Write-Host "Starting services..." -ForegroundColor Blue
    docker-compose up -d
    
    Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Check backend health
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "✓ Backend is ready" -ForegroundColor Green
                break
            }
        }
        catch {
            Write-Host "Waiting for backend... (attempt $($attempt+1)/$maxAttempts)" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
            $attempt++
        }
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "✗ Backend failed to start" -ForegroundColor Red
        exit 1
    }
}

# Initialize database
function Initialize-Database {
    Write-Host ""
    Write-Host "Initializing database..." -ForegroundColor Blue
    
    # Run migrations
    docker-compose exec -T backend python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
    
    Write-Host "✓ Database initialized" -ForegroundColor Green
}

# Print service URLs
function Show-ServiceInfo {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║    Academic Content Generator is ready!                        ║" -ForegroundColor Green
    Write-Host "╠════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
    Write-Host "║ Frontend:        http://localhost:3000                         ║" -ForegroundColor Green
    Write-Host "║ Backend API:     http://localhost:8000                         ║" -ForegroundColor Green
    Write-Host "║ API Docs:        http://localhost:8000/docs                    ║" -ForegroundColor Green
    Write-Host "║ PostgreSQL:      localhost:5432                                ║" -ForegroundColor Green
    Write-Host "║ Redis:           localhost:6379                                ║" -ForegroundColor Green
    Write-Host "║ ChromaDB:        http://localhost:8001                         ║" -ForegroundColor Green
    Write-Host "╠════════════════════════════════════════════════════════════════╣" -ForegroundColor Green
    Write-Host "║ Database Credentials:                                          ║" -ForegroundColor Green
    Write-Host "║   User: user                                                   ║" -ForegroundColor Green
    Write-Host "║   Password: password                                           ║" -ForegroundColor Green
    Write-Host "║   Database: academic_generator                                 ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "To stop services: docker-compose down" -ForegroundColor Gray
    Write-Host "To view logs: docker-compose logs -f" -ForegroundColor Gray
    Write-Host "To stop and remove data: docker-compose down -v" -ForegroundColor Gray
}

# Main setup flow
function Main {
    Write-Host ""
    
    # Check prerequisites
    if (-not (Test-Docker)) { exit 1 }
    if (-not (Test-DockerCompose)) { exit 1 }
    
    # Setup
    Initialize-Env
    if (-not $SkipBuild) { Invoke-Build }
    Start-Services
    Initialize-Database
    
    # Display information
    Show-ServiceInfo
}

# Run main
Main
