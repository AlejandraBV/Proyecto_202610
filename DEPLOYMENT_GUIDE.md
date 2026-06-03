# 🎓 Academic Content Generator - Deployment Guide

## 📋 Overview

**Academic Content Generator v2.0** es una aplicación web AI-powered para generar contenido académico con:

- 🤖 **RAG Pipeline**: Ingesta de documentos (PDF/DOCX), chunking semántico, búsqueda vectorial
- 🧠 **4 Agentes Especializados**: Analyzer, Generator, Reviewer, Feedback Agent
- 🔄 **Human-in-the-Loop (HITL)**: Ciclos infinitos de regeneración basada en feedback
- 📁 **Organización por Carpetas**: Chats organizados por tema/asignatura con detección automática de cambio de tema
- 📚 **Multi-LLM Support**: Gemini 1.5 Pro (default) o GPT-4o
- 🔐 **Autenticación JWT**: User isolation y role-based access
- 🎨 **Frontend Moderno**: Next.js 14 con TypeScript y Tailwind CSS

---

## 🚀 Quick Start (Local Deployment)

### Prerequisites

- **Docker Desktop** (incluye Docker y Docker Compose)
  - [Descargar para Windows](https://www.docker.com/products/docker-desktop)
  - [Descargar para Mac](https://www.docker.com/products/docker-desktop)
  - [Descargar para Linux](https://docs.docker.com/engine/install/)

- **Git** (para clonar el repositorio)

### 1. Preparar configuración

```bash
# Clone the repository
git clone <repository-url>
cd Proyecto_202610

# Copy example environment file
cp .env.example .env
```

Edita `.env` con tus API keys:

```env
# Elige uno de estos LLM providers
LLM_PROVIDER=gemini
GOOGLE_API_KEY=sk-XXXXXXXXXXXX  # https://aistudio.google.com/apikey
# OR
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-XXXXXXXXXXXX   # https://platform.openai.com/api-keys
```

### 2. Ejecutar con Docker Compose

#### **Windows (PowerShell)**
```powershell
# Con script automatizado
.\setup-local.ps1

# O manualmente
docker-compose up -d
# Espera 30 segundos para que inicie
```

#### **Linux/Mac (Bash)**
```bash
# Con script automatizado
chmod +x setup-local.sh
./setup-local.sh

# O manualmente
docker-compose up -d
# Espera 30 segundos para que inicie
```

### 3. Acceder a la aplicación

```
Frontend:    http://localhost:3000
API:         http://localhost:8000
API Docs:    http://localhost:8000/docs
```

**Crear usuario de prueba:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@example.com",
    "password": "password123",
    "name": "Prof. John Doe",
    "institution": "MIT",
    "subject": "Biology"
  }'
```

---

## 🏗️ Architecture

### Database Schema

```
Users
├── Folders (organización por tema)
│   └── Conversations
│       ├── Messages
│       ├── GeneratedContent
│       │   └── FeedbackRecords
│       └── AgentDecisionRecords
└── Documents (RAG)
    └── Chunks (vectorizados)

TopicChangeLogs (auditoría de cambios automáticos)
```

### Services Included

| Servicio | Puerto | Propósito |
|----------|--------|-----------|
| **PostgreSQL** | 5432 | Base de datos principal |
| **FastAPI Backend** | 8000 | API REST + WebSocket |
| **Next.js Frontend** | 3000 | Interfaz web |
| **Redis** | 6379 | Cache y sesiones |
| **ChromaDB** | 8001 | Vector database para RAG |

---

## 📁 Nuevas Características: Folders & Topic Detection

### 1. **Organización por Carpetas**

```javascript
// Obtener carpetas del usuario
GET /folders

// Crear nueva carpeta
POST /folders
{
  "name": "Biología",
  "description": "Conversaciones sobre biología",
  "color": "#10B981",
  "icon": "📚",
  "is_default": true
}

// Actualizar carpeta
PUT /folders/{folder_id}

// Eliminar carpeta (mueve chats a carpeta default)
DELETE /folders/{folder_id}

// Obtener chats de una carpeta
GET /folders/{folder_id}/conversations
```

### 2. **Detección Automática de Cambio de Tema**

El sistema detecta cuando el usuario cambia de tema y **crea automáticamente un nuevo chat** para evitar contaminación de contexto:

```
Usuario en Chat: "Biología" (locked_topic)
├─ Pregunta 1: Fotosíntesis ✓ (tema consistente)
├─ Pregunta 2: Respiración celular ✓ (tema consistente)
└─ Pregunta 3: "Ahora dime de matemáticas" 
   ↓ DETECTED TOPIC CHANGE
   → Nuevo Chat automático creado para "Matemáticas"
   → Anterior chat se finaliza
   → Log de cambio guardado en TopicChangeLogs
```

**Configuración:**
```python
# backend/app/core/config.py
REVIEWER_CONFIDENCE_THRESHOLD = 0.85  # Score mínimo para cambio automático
```

### 3. **Frontend: Sidebar con Carpetas**

```typescript
// Nueva estructura en store
{
  folders: Folder[],
  conversations: ConversationsByFolder,
  activeFolder: string,
  activeChat: string,
}

// Componente Sidebar
<Sidebar>
  <FolderTree folders={folders}>
    {folder.conversations.map(chat => (
      <ChatItem key={chat.id} chat={chat} />
    ))}
  </FolderTree>
</Sidebar>
```

---

## 🔧 Configuración Avanzada

### Variables de Entorno

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/academic_generator

# LLM Configuration
LLM_PROVIDER=gemini              # "gemini" o "openai"
GOOGLE_API_KEY=...
OPENAI_API_KEY=...

# Agent Settings
MAX_AGENT_ITERATIONS=3           # Re-ranking máximo
AGENT_TIMEOUT=60                 # Segundos por agente
REVIEWER_CONFIDENCE_THRESHOLD=0.85 # Score para aprobar

# Vector Database
CHROMA_DIR=./chromadb_data
CHUNK_SIZE=1500
CHUNK_OVERLAP=0.12               # 12% overlap

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
DEBUG=False
CORS_ORIGINS=http://localhost:3000
```

### Cambiar LLM Provider

```bash
# Usar Gemini (default)
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY=sk-...

# O usar GPT-4o
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

docker-compose up -d
```

---

## 📊 API Endpoints

### Authentication
```
POST   /auth/register           # Registrar usuario
POST   /auth/login              # Login y obtener JWT
```

### Folders
```
GET    /folders                 # Listar carpetas del usuario
POST   /folders                 # Crear carpeta
GET    /folders/{id}            # Obtener carpeta
PUT    /folders/{id}            # Actualizar carpeta
DELETE /folders/{id}            # Eliminar carpeta
GET    /folders/{id}/conversations  # Conversaciones en carpeta
```

### Conversations
```
GET    /conversations           # Listar chats del usuario
POST   /conversations           # Crear chat
GET    /conversations/{id}      # Obtener chat con mensajes
PUT    /conversations/{id}      # Actualizar chat
DELETE /conversations/{id}      # Eliminar chat
```

### Content Generation
```
POST   /conversations/{id}/messages         # Generar contenido
POST   /conversations/{id}/regenerate       # Regenerar con feedback
```

### Documents (RAG)
```
POST   /documents/upload        # Upload PDF/DOCX
GET    /documents/search        # Búsqueda semántica
DELETE /documents/{id}          # Eliminar documento
```

### Feedback Loop
```
POST   /feedback                # Enviar feedback
GET    /feedback/learning-examples  # Obtener ejemplos para few-shot
```

---

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "version": "2.0.0"}
```

### API Documentation
```
http://localhost:8000/docs           # Swagger UI
http://localhost:8000/redoc          # ReDoc
```

### Test Integration Completa
```bash
# Desde dentro del contenedor
docker-compose exec backend pytest tests/ -v

# O desde tu máquina (requiere Python)
cd backend
python -m pytest tests/ -v
```

---

## 🐛 Troubleshooting

### "Port 8000 already in use"
```bash
# Cambiar puerto en docker-compose.yml
BACKEND_PORT=8001 docker-compose up -d
```

### "Database connection refused"
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose logs postgres

# Reiniciar servicios
docker-compose restart postgres backend
```

### "API key invalid"
```bash
# Verificar en .env
cat .env | grep API_KEY

# Actualizar .env
nano .env  # Edit y guarda
docker-compose restart backend
```

### "Frontend no carga"
```bash
# Verificar conexión al backend
curl http://localhost:8000/health

# Ver logs del frontend
docker-compose logs -f frontend
```

---

## 📈 Performance Tuning

### Para desarrollo
```bash
# Modo reload automático
command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Para producción
```bash
# Desactivar debug, usar Gunicorn
command: gunicorn main:app -w 4 --worker-class uvicorn.workers.UvicornWorker
DEBUG=False
```

### Optimizar RAG
```python
# backend/app/core/config.py
CHUNK_SIZE = 1500          # Aumentar para docs grandes
CHUNK_OVERLAP = 0.15       # Aumentar para mejor contexto
MAX_DOCUMENT_SIZE = 100_000_000  # 100MB
```

---

## 🔐 Security Checklist

- [ ] Cambiar `SECRET_KEY` en `.env`
- [ ] Usar API keys reales (no test keys)
- [ ] Habilitar HTTPS en producción
- [ ] Usar variables de entorno para secrets
- [ ] Limitar CORS_ORIGINS
- [ ] Cambiar contraseña default de PostgreSQL
- [ ] Hacer backup de `chromadb_data/` y `postgres_data/`

---

## 🛑 Detener y Limpiar

```bash
# Detener servicios (mantiene datos)
docker-compose down

# Detener y eliminar datos
docker-compose down -v

# Ver logs en vivo
docker-compose logs -f

# Reiniciar todo
docker-compose restart
```

---

## 📚 Documentation

- [Backend README](./backend/README.md)
- [Frontend README](./frontend/README.md)
- [PDF Specification](./Propuesta_202610.pdf)
- [Architecture Analysis](./ARCHITECTURE_ANALYSIS.md)

---

## 🤝 Support

Si encuentras problemas:

1. Verifica que Docker está corriendo: `docker ps`
2. Revisa los logs: `docker-compose logs -f backend`
3. Prueba health check: `curl http://localhost:8000/health`
4. Lee troubleshooting section arriba
5. Abre un issue en GitHub

---

**Made with ❤️ for educators**  
Academic Content Generator v2.0 | 2024
