#!/bin/bash

## ======================================================================
## SETUP AUTOMATICO - ACADEMIC CONTENT GENERATOR
## VM: Ubuntu 24, 4 CPU, 16GB RAM
## ======================================================================

echo "🚀 Iniciando setup de Academic Content Generator..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ======================================================================
# 1. ACTUALIZAR SISTEMA
# ======================================================================
echo -e "\n${YELLOW}📦 Actualizando sistema...${NC}"
sudo apt update
sudo apt upgrade -y

# ======================================================================
# 2. INSTALAR POSTGRESQL
# ======================================================================
echo -e "\n${YELLOW}🗄️  Instalando PostgreSQL...${NC}"
sudo apt install postgresql postgresql-contrib -y

# Iniciar PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Crear usuario y database
echo -e "${YELLOW}📝 Creando usuario y database...${NC}"
sudo -u postgres psql << EOF
CREATE USER academic WITH PASSWORD 'academic_secure_pass';
ALTER USER academic CREATEDB;
CREATE DATABASE academic_generator OWNER academic;
GRANT ALL PRIVILEGES ON DATABASE academic_generator TO academic;
EOF

echo -e "${GREEN}✅ PostgreSQL configurado${NC}"

# ======================================================================
# 3. INSTALAR PYTHON 3.11
# ======================================================================
echo -e "\n${YELLOW}🐍 Instalando Python 3.11...${NC}"
sudo apt install python3.11 python3.11-venv python3-pip -y
python3.11 --version

# ======================================================================
# 4. INSTALAR NODE.JS 20
# ======================================================================
echo -e "\n${YELLOW}📦 Instalando Node.js 20...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y
node --version
npm --version

# ======================================================================
# 5. INSTALAR GIT (si no está)
# ======================================================================
echo -e "\n${YELLOW}🔧 Instalando Git...${NC}"
sudo apt install git -y

# ======================================================================
# 6. INSTALAR TMUX (para correr procesos en background)
# ======================================================================
echo -e "\n${YELLOW}🔌 Instalando Tmux...${NC}"
sudo apt install tmux -y

# ======================================================================
# 7. CREAR ESTRUCTURA DE DIRECTORIOS
# ======================================================================
echo -e "\n${YELLOW}📁 Creando estructura de proyecto...${NC}"
mkdir -p ~/app
cd ~/app

# Si tienes git, puedes clonar. Si no, asumimos que copiaste los archivos
# git clone <tu-repo> Proyecto_202610
# Por ahora asumimos estructura existente

# ======================================================================
# 8. SETUP BACKEND
# ======================================================================
echo -e "\n${YELLOW}⚙️  Configurando Backend...${NC}"

mkdir -p ~/app/backend
cd ~/app/backend

# Crear virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Crear requirements.txt si no existe
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << 'REQS'
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
python-jose>=3.3.0
passlib>=1.7.0
python-multipart>=0.0.6
langchain>=0.1.0
langgraph>=0.0.1
langchain-google-genai>=0.0.8
chromadb>=0.4.0
python-dotenv>=1.0.0
google-generativeai>=0.3.0
httpx>=0.25.0
email-validator>=2.0.0
REQS
fi

# Instalar dependencias
pip install -r requirements.txt

# Crear .env
cat > .env << 'ENV'
# ============================================
# CONFIGURACION - Academic Content Generator
# ============================================

# Base de Datos
DATABASE_URL=postgresql+asyncpg://academic:academic_secure_pass@localhost:5432/academic_generator

# JWT
SECRET_KEY=cambiar-esto-en-produccion-$(date +%s)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Gemini (USA TU COUPON AQUI)
GOOGLE_API_KEY=TU_GOOGLE_API_KEY_AQUI
GEMINI_MODEL=gemini-1.5-pro

# LLM Configuration
LLM_PROVIDER=gemini

# ChromaDB
CHROMA_DIR=./chromadb_data

# App Settings
APP_NAME=Academic Content Generator
DEBUG=False
CORS_ORIGINS=["http://localhost:3000","http://172.24.99.7:3000"]
ENV

echo -e "${GREEN}✅ Backend configurado${NC}"
echo -e "${YELLOW}⚠️  IMPORTANTE: Edita backend/.env y añade tu GOOGLE_API_KEY${NC}"

# ======================================================================
# 9. SETUP FRONTEND
# ======================================================================
echo -e "\n${YELLOW}🎨 Configurando Frontend...${NC}"

mkdir -p ~/app/frontend
cd ~/app/frontend

# Instalar dependencias Node
npm install

# Crear .env.local
cat > .env.local << 'FENV'
NEXT_PUBLIC_API_URL=http://172.24.99.7:8000
FENV

echo -e "${GREEN}✅ Frontend configurado${NC}"

# ======================================================================
# 10. CREAR SCRIPT DE INICIO
# ======================================================================
echo -e "\n${YELLOW}🚀 Creando scripts de inicio...${NC}"

cat > ~/start-app.sh << 'START'
#!/bin/bash

echo "🚀 Iniciando Academic Content Generator..."
echo "📍 Backend: http://172.24.99.7:8000"
echo "📍 Frontend: http://172.24.99.7:3000"
echo "📍 API Docs: http://172.24.99.7:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Iniciar Backend en tmux
echo "⚙️  Iniciando Backend..."
tmux new-session -d -s backend -c ~/app/backend 'source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000'
sleep 3

# Iniciar Frontend en tmux
echo "🎨 Iniciando Frontend..."
tmux new-session -d -s frontend -c ~/app/frontend 'npm run dev'
sleep 3

echo ""
echo "✅ Aplicación iniciada!"
echo ""
echo "📝 Para ver logs:"
echo "   Backend:  tmux attach -t backend"
echo "   Frontend: tmux attach -t frontend"
echo ""
echo "🛑 Para detener:"
echo "   tmux kill-session -t backend"
echo "   tmux kill-session -t frontend"
echo ""
START

chmod +x ~/start-app.sh

cat > ~/stop-app.sh << 'STOP'
#!/bin/bash
echo "🛑 Deteniendo aplicación..."
tmux kill-session -t backend
tmux kill-session -t frontend
echo "✅ Detenido"
STOP

chmod +x ~/stop-app.sh

cat > ~/logs.sh << 'LOGS'
#!/bin/bash
echo "Selecciona:"
echo "1) Backend logs"
echo "2) Frontend logs"
echo "3) Ambos"
read -p "Opción: " choice

case $choice in
    1) tmux attach -t backend ;;
    2) tmux attach -t frontend ;;
    3) 
        echo "Abre otra terminal para ver ambos:"
        echo "tmux attach -t backend"
        echo "tmux attach -t frontend"
        tmux attach -t backend
        ;;
esac
LOGS

chmod +x ~/logs.sh

echo -e "${GREEN}✅ Scripts de inicio creados${NC}"

# ======================================================================
# 11. MOSTRAR RESUMEN
# ======================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ SETUP COMPLETADO${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo ""
echo "1️⃣  Editar configuración:"
echo "   nano ~/app/backend/.env"
echo "   - Edita: GOOGLE_API_KEY=tu_clave_aqui"
echo ""
echo "2️⃣  Iniciar aplicación:"
echo "   ~/start-app.sh"
echo ""
echo "3️⃣  Ver logs:"
echo "   ~/logs.sh"
echo ""
echo "4️⃣  Detener:"
echo "   ~/stop-app.sh"
echo ""
echo "🌐 Acceder desde tu laptop:"
echo "   Frontend:  http://172.24.99.7:3000"
echo "   Backend:   http://172.24.99.7:8000"
echo "   API Docs:  http://172.24.99.7:8000/docs"
echo ""
echo "💰 Coupon GCP:"
echo "   Solo se usa para llamadas a Gemini API"
echo "   Todo lo demás es GRATIS en la VM"
echo ""
