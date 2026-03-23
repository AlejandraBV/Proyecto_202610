#!/bin/bash

# This script sets up the entire development environment

echo "🚀 Setting up Academic Content Generator..."

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 20+"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.11+"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client not found. You'll need to set up the database manually."
fi

echo "✅ Prerequisites OK"

# Setup Backend
echo -e "\n📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate || source venv/Scripts/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env with your API keys"
fi

cd ..

# Setup Frontend
echo -e "\n🎨 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
fi

if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file..."
    cp .env.local.example .env.local
fi

cd ..

echo -e "\n✨ Setup complete!"
echo -e "\n📚 Next steps:"
echo "1. Edit backend/.env with your API keys"
echo "2. Ensure PostgreSQL is running (or use docker-compose)"
echo "3. Run: npm run dev:all (runs both frontend and backend)"
echo "   OR run separately:"
echo "   - Backend: cd backend && uvicorn main:app --reload"
echo "   - Frontend: cd frontend && npm run dev"
echo -e "\n🌐 Access at http://localhost:3000"
