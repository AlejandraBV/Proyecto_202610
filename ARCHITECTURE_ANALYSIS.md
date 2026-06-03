# 📊 Análisis Completo de Arquitectura - Academic Content Generator

## 🎯 RESUMEN EJECUTIVO

Sistema **integral de IA** para generación de contenido académico con:
- ✅ Backend FastAPI + SQLAlchemy + PostgreSQL async
- ✅ Frontend Next.js/React/TypeScript con estado global
- ✅ RAG pipeline con ChromaDB para búsqueda semántica
- ✅ Agentes LLM (Gemini 1.5 Pro / GPT-4o) multi-etapa
- ✅ Retroalimentación humana con aprendizaje (HITL)
- ✅ Gestión completa de conversaciones y documentos

---

## 📦 1. ESTRUCTURA COMPLETA DE BASE DE DATOS

### Diagrama de Relaciones
```
┌─────────────┐
│    User     │ (Docentes)
├─────────────┤
│ id (UUID)   │
│ email       │
│ password    │
│ name        │
│ institution │
│ subject     │
│ level       │
│ is_active   │
└──────┬──────┘
       │ 1:many
       │
       ├──────────────────────────────────┐
       │                                  │
   ┌───┴─────────┐          ┌────────────┴─────┐
   │ Conversation│          │    Document      │
   ├─────────────┤          ├──────────────────┤
   │ id (UUID)   │          │ id (UUID)        │
   │ user_id(FK) │          │ user_id (FK)     │
   │ title       │          │ conversation_id  │
   │ subject     │          │ filename         │
   │ topic       │          │ file_type        │
   │ primary_*   │          │ original_content │
   │ all_topics  │          │ chunks_count     │
   │ created_at  │          │ vector_index_ids │
   └───┬─────────┘          └────────┬─────────┘
       │ 1:many                      │ 1:many
       │                             │
   ┌───┴──────────┐         ┌────────┴────────┐
   │   Message    │         │     Chunk      │
   ├──────────────┤         ├─────────────────┤
   │ id (UUID)    │         │ id (UUID)       │
   │ conv_id (FK) │         │ doc_id (FK)     │
   │ role         │         │ chunk_index     │
   │ content      │         │ text            │
   │ subject      │         │ vector_id       │
   │ topic        │         │ chunk_size      │
   │ detected_*   │         │ overlap_info    │
   └──────────────┘         └─────────────────┘
       │
       │
   ┌───┴──────────────────┐
   │ GeneratedContent     │
   ├──────────────────────┤
   │ id (UUID)            │
   │ conversation_id (FK) │
   │ content_type         │ ◄─── exam|slideshow|guide|question|text
   │ title, content       │
   │ feedback             │
   │ version              │
   │ total_regen_attempts │ ◄─── Conteo HITL sin límite
   │ review_score         │
   └────┬─────────────────┘
        │ 1:many
        │
    ┌───┴──────────────┐
    │  FeedbackRecord  │
    ├──────────────────┤
    │ id (UUID)        │
    │ content_id (FK)  │
    │ feedback (text)  │
    │ status           │ ◄─── approved|needs_revision|rejected
    │ editor_name      │
    │ timestamp        │
    └──────────────────┘

┌──────────────────────────────┐
│  AgentDecisionRecord         │ (Auditoría)
├──────────────────────────────┤
│ id (UUID)                    │
│ conversation_id (FK)         │
│ agent_name                   │ ◄─── analyzer|generator|reviewer|feedback
│ decision, reasoning          │
│ quality_score, iteration     │
│ timestamp                    │
└──────────────────────────────┘
```

### Detalle de Modelos

| Modelo | Propósito | Campos Clave | Relaciones |
|--------|-----------|--------------|-----------|
| **User** | Perfil de docente | id, email, hashed_password, name, institution, subject, level, is_active | conversations (1:∞), documents (1:∞) |
| **Conversation** | Sesión de chat | id, user_id, title, subject, topic, primary_subject, primary_topic, all_topics | user (∞:1), messages (1:∞), generated_contents (1:∞), documents (1:∞) |
| **Message** | Mensaje en conversación | id, conversation_id, role ('user'\|'assistant'), content, subject, topic, detected_content_type, detection_confidence | conversation (∞:1) |
| **GeneratedContent** | Contenido generado | id, conversation_id, content_type, title, content, version, total_regeneration_attempts, review_score | conversation (∞:1), feedback_records (1:∞) |
| **FeedbackRecord** | Retroalimentación docente | id, content_id, feedback, status, editor_name, timestamp | content (∞:1) |
| **Document** | Documento para RAG | id, user_id, conversation_id, filename, file_type, original_content, chunks_count, vector_index_ids | user (∞:1), conversation (∞:1), chunks (1:∞) |
| **Chunk** | Fragmento vectorizado | id, document_id, chunk_index, text, chunk_size, vector_id | document (∞:1) |
| **AgentDecisionRecord** | Auditoría de agentes | id, conversation_id, agent_name, decision, reasoning, quality_score, iteration | conversation (∞:1) |

---

## 🔌 2. ENDPOINTS FASTAPI COMPLETOS

### **Router: /auth** (Autenticación)
```
POST /auth/register
├─ Input: UserCreate (email, password, name, institution)
├─ Validaciones: Email único, password hash
└─ Output: UserResponse (id, email, name, created_at)

POST /auth/login
├─ Input: email, password
├─ Genera: JWT token (HS256, 30 min expiry)
└─ Output: TokenResponse (access_token, token_type='bearer')
```

### **Router: /conversations** (Gestión de chats)
```
GET /conversations
├─ Auth: Bearer token requerido
├─ Eager load: messages, generated_contents
└─ Output: List[ConversationResponse]

GET /conversations/{id}
├─ Auth: Bearer token + user_id verification
├─ Eager load: messages, generated_contents
└─ Output: ConversationResponse

POST /conversations
├─ Auth: Bearer token
├─ Input: ConversationCreate (title, subject?, topic?)
└─ Output: ConversationResponse (nueva conversación)

POST /conversations/{id}/messages (⭐ ENDPOINT CRÍTICO)
├─ Auth: Bearer token
├─ Input: MessageRequest (user_prompt, conversation_id?, document_id?, difficulty?)
├─ Pipeline:
│  1. MetadataAnalyzer → detecta subject, topic, content_type
│  2. Si document_id → RAG retrieval de chunks relevantes
│  3. ContentOrchestrator.generate_with_rag_and_agents()
│  4. Guardar message + GeneratedContent en BD
│  5. Registrar AgentDecisionRecords
├─ Output: RoutedMessageResponse
│         (conversation_id, is_new_conversation, subject, topic,
│          content_type, confidence, detection_method, content, title)
└─ Genera contenido mediante pipeline multi-agente

POST /conversations/{id}/generate
├─ Auth: Bearer token
├─ Input: GenerationRequest (content_type, subject, topic, level)
├─ Pipeline: Analyzer → Generator → Reviewer (+ loop HITL)
└─ Output: GenerationResponse (contenido generado)

PATCH /conversations/{id}
├─ Auth: Bearer token
├─ Input: ConversationUpdate (title?, subject?, topic?, last_edited?)
└─ Output: ConversationResponse

DELETE /conversations/{id}
├─ Auth: Bearer token
├─ Cascade delete: messages, generated_contents
└─ Output: 200 OK
```

### **Router: /documents** (Gestión RAG)
```
POST /documents/upload (⭐ CRÍTICO PARA RAG)
├─ Auth: Bearer token
├─ Input: File (PDF|DOCX|TXT), subject, topic?, conversation_id?
├─ Validaciones:
│  ├─ File type: pdf, docx, txt solamente
│  └─ File size: max 50MB
├─ Processing Pipeline:
│  1. DocumentIngestor.parse_file() → extrae texto
│  2. SemanticChunker → chunks de 1500 chars, 12% overlap
│  3. VectorDatabaseService.add_documents() → ChromaDB
│  4. Guardar Document + Chunks en BD PostgreSQL
│  5. Indexar en vector_index_ids (JSON)
├─ Output: DocumentResponse
│         (id, filename, file_type, chunks_count, created_at)
└─ El documento queda disponible para RAG retrieval

GET /documents
├─ Auth: Bearer token
├─ Output: List[DocumentResponse]

GET /documents/{id}
├─ Auth: Bearer token
├─ Eager load: chunks preview (primeros 5)
└─ Output: DocumentResponse + chunks[]

GET /documents/{id}/chunks
├─ Auth: Bearer token
├─ Pagination: limit=10, offset=0
└─ Output: List[ChunkResponse] (id, text, chunk_index, vector_id)

DELETE /documents/{id}
├─ Auth: Bearer token
├─ Cascade: Elimina chunks de ChromaDB + PostgreSQL
└─ Output: 200 OK
```

### **Router: /feedback** (Retroalimentación HITL)
```
POST /feedback/{content_id} (⭐ CICLO DE RETROALIMENTACIÓN)
├─ Auth: Bearer token
├─ Input: FeedbackSubmit (feedback, status, editor_name?)
├─ Status: 'approved' | 'needs_revision' | 'rejected'
├─ Pipeline:
│  1. Guardar FeedbackRecord en BD
│  2. Si status='needs_revision' || 'rejected':
│  │  └─ Trigger regeneración con feedback como contexto
│  3. Si status='approved':
│  │  └─ Guardar como learning example para few-shot future
│  4. Actualizar GeneratedContent.review_score
│  5. Incrementar GeneratedContent.total_regeneration_attempts
├─ Output: Dict (feedback_id, next_action)
└─ Permite ciclos infinitos de mejora (HITL Loop)

GET /feedback/{content_id}
├─ Auth: Bearer token
├─ Output: List[FeedbackRecordResponse] (historial completo)
```

### **Router: /health** (Monitoreo)
```
GET /health
└─ Output: {"status": "healthy"}
```

---

## 🎨 3. COMPONENTES FRONTEND REACT/NEXT.JS

### **Estructura de Páginas** [frontend/pages/]
```
pages/
├── index.tsx (Home principal - Chat interface)
├── dashboard.tsx (Overview + Stats del docente)
├── login.tsx (Formulario de login)
├── register.tsx (Formulario de registro)
├── documents.tsx (Gestor de documentos para RAG)
├── settings.tsx (Configuración de perfil)
└── conversations/
    └── [id].tsx (Conversación individual)
```

### **Árbol de Componentes** [frontend/components/]

```
Layout.tsx (Wrapper principal)
├── header (Navigation, user profile)
├── Sidebar.tsx (Lista de conversaciones)
│  ├── Subject emoji mapping
│  ├── Timestamp relativo (date-fns)
│  ├── Delete button
│  └── New conversation button
├── ChatWindow.tsx (Display de mensajes)
│  ├── ScrollArea (auto-scroll)
│  ├── MessageItem[] (iterado)
│  │  ├── User message bubble
│  │  ├── Assistant message bubble
│  │  ├── Markdown rendering
│  │  ├── Metadata badges
│  │  └── Loading skeleton
│  └── Empty state
├── ChatInput.tsx (Input de usuario)
│  ├── Textarea (multiline, auto-expand)
│  ├── Envío con Enter
│  ├── Loading indicator
│  └── Character counter
├── ContentEditor.tsx (Edit/Preview para contenido)
│  ├── Edit mode (textarea)
│  ├── Preview mode (markdown rendered)
│  ├── Save button
│  └── Cancel button
├── ContentPreview.tsx (Display-only preview)
│  ├── Markdown rendering
│  └── Metadata display
├── DocumentUploader.tsx (Drag-drop upload)
│  ├── File validation
│  ├── Progress bar
│  ├── Subject/Topic inputs
│  └── Error messages
├── FeedbackPanel.tsx (Retroalimentación interactiva)
│  ├── Textarea para feedback
│  ├── Radio buttons (approved|needs_revision|rejected)
│  ├── Submit button
│  └── Feedback history
├── RegenerationButton.tsx (Trigger re-gen)
│  └── Envía trigger al backend
└── ScrollArea.tsx (Custom scroll wrapper)
   └── Auto-scroll to bottom on new messages
```

### **Component Details**

| Componente | Props | Estado | Funcionalidad |
|-----------|-------|--------|--------------|
| **ChatWindow** | conversation, isLoading | Ninguno (props) | Display mensajes, scroll, empty state |
| **ChatInput** | onSend | inputValue, isExpanded | Input multiline, envío, loading |
| **Sidebar** | conversations[], currentId, handlers | Ninguno | Lista de chats, selección, delete |
| **MessageItem** | message, isLoading | Ninguno | Render user/assistant, markdown, badges |
| **ContentEditor** | content, onSave, readOnly | editMode, text, isSaving | Toggle edit/preview, save |
| **DocumentUploader** | onUpload | fileList, uploading, progress | Drag-drop, validation, upload |
| **FeedbackPanel** | contentId, onSubmit | feedback, status, isSending | Feedback form, history |
| **Layout** | children | userMenu open? | Header + nav + content |
| **Sidebar** | conversations, selected | currentConvId | Conv list, active state, delete |

---

## 💬 4. SISTEMA DE CONVERSACIONES Y CHATS

### **Backend: ConversationService**
```python
# backend/app/services/conversation_service.py

class ConversationService:
    
    @staticmethod
    async def get_conversations_by_user(db, user_id) → List[Conversation]
    # Fetch todas conversaciones con eager load de messages + generated_contents
    
    @staticmethod
    async def get_conversation(db, conversation_id, user_id) → Conversation
    # Fetch específica + security check (user_id debe coincidir)
    
    @staticmethod
    async def create_conversation(db, user_id, title, subject?, topic?) → Conversation
    # Crear nueva conversación, auto-gen UUID
    
    @staticmethod
    async def add_message(db, conversation_id, role, content, ...) → Message
    # Crear mensaje + guardar metadata auto-detectada
    
    @staticmethod
    async def get_messages(db, conversation_id) → List[Message]
    # Fetch ordenadas por timestamp, con metadata completa
    
    @staticmethod
    async def update_conversation(db, conversation_id, updates) → Conversation
    # Update title, subject, topic, last_edited timestamp
```

### **Frontend: Global State with Zustand**
```typescript
// frontend/store/appStore.ts

interface AppStore {
  // User
  currentUser: UserProfile | null
  setCurrentUser(user: UserProfile)
  
  // Conversations
  conversations: ConversationThread[]
  currentConversation: ConversationThread | null
  setConversations(convs: ConversationThread[])
  setCurrentConversation(conv: ConversationThread | null)
  addConversation(conv: ConversationThread)
  updateConversation(id: string, updates: Partial<ConversationThread>)
  
  // Messages (dentro de currentConversation)
  addMessage(conversationId: string, msg: Message)
  updateMessages(conversationId: string, msgs: Message[])
  
  // Generated Content
  addGeneratedContent(conversationId: string, content: GeneratedContent)
  updateGeneratedContent(id: string, updates: Partial<GeneratedContent>)
  
  // Documents (RAG)
  documents: Document[]
  addDocument(doc: Document)
  setDocuments(docs: Document[])
  
  // Chunks para RAG debugging
  retrievedChunks: ChunkResponse[]
  setRetrievedChunks(chunks: ChunkResponse[])
  
  // UI
  loading: boolean
  error: string | null
  showRetrievedChunks: boolean
}
```

### **Frontend: Chat Flow**

```
User types in ChatInput
      │
      ▼
handleSendMessage()
      │
      ├─ Create tempUserMessage
      ├─ Add to store (currentConversation.messages)
      ├─ setInputValue('')
      └─ setLoading(true)
      │
      ▼
POST /conversations/{id}/messages
      │ (Backend processes through Content Orchestrator)
      │
      ▼
Response: RoutedMessageResponse
      │
      ├─ conversation_id
      ├─ is_new_conversation (boolean)
      ├─ subject, topic (auto-detected)
      ├─ content_type, confidence, detection_method
      ├─ content (generated output)
      └─ title (para nueva conversación)
      │
      ▼
Update Store:
      ├─ Si is_new_conversation: addConversation()
      ├─ setCurrentConversation()
      ├─ Crear assistantMessage {role: 'assistant', content: response.content}
      ├─ addMessage(currentConversation.id, assistantMessage)
      └─ setLoading(false)
      │
      ▼
ChatWindow re-renders con nuevo mensaje
      └─ ScrollArea auto-scrolls to bottom
```

### **Metadata Detection Flow**

```
User prompt: "Create an exam about photosynthesis for university level"
      │
      ▼
MetadataAnalyzer.analyze_prompt()
      │
      ├─ Layer 1: Keyword matching
      │  ├─ Search KEYWORD_DATABASE[Biology][*] para "photosynthesis"
      │  ├─ Match found → subject=Biology, topic=Photosynthesis
      │  └─ confidence=1.0, method='keywords'
      │
      └─ Si no match → Layer 2: LLM analysis (fallback)
         └─ Call LLM para parse implícito
      │
      ▼
Content Type Detection:
      ├─ Search CONTENT_TYPE_KEYWORDS['exam'] para "exam"
      ├─ Match → content_type='exam'
      └─ confidence=1.0
      │
      ▼
Return: {
  subject: 'Biology',
  topic: 'Photosynthesis',
  content_type: 'exam',
  difficulty: 'university',
  confidence: 0.95,
  detection_method: 'keywords'
}
```

---

## 🤖 5. PIPELINE RAG + AGENTES

### **Content Orchestrator Main Flow**

```
User request in conversation
      │
      ▼
ContentOrchestrator.generate_with_rag_and_agents()
      │
      ├─ Step 1: ANALYZE
      │  │
      │  └─ AnalyzerAgent.analyze_with_context()
      │     ├─ Parse user prompt
      │     ├─ MetadataAnalyzer → subject, topic, content_type
      │     ├─ RAGService.retrieve() → chunks relevantes
      │     │  └─ ChromaDB query con semantic search
      │     └─ Extract requirements from prompt
      │
      ├─ Step 2: GENERATE
      │  │
      │  └─ GeneratorAgent.generate()
      │     ├─ Build enhanced prompt:
      │     │  ├─ System: "You are expert academic content generator"
      │     │  ├─ Context: {subject, topic, level, content_type}
      │     │  ├─ RAG chunks: Retrieved context
      │     │  └─ Few-shot examples: Approved feedback (learning)
      │     ├─ Call LLMService (Gemini / GPT-4o)
      │     └─ Return: generated content
      │
      ├─ Step 3: REVIEW
      │  │
      │  └─ ReviewerAgent.validate()
      │     ├─ Check quality (0-1 score)
      │     ├─ Verify requirements met
      │     ├─ Check difficulty level appropriate
      │     └─ Return: {pass: bool, score: float, feedback: str}
      │
      ├─ Step 4: DECISION LOOP
      │  │
      │  ├─ If review.pass=true:
      │  │  └─ Proceed to Step 5 (Save & Return)
      │  │
      │  └─ If review.pass=false:
      │     ├─ Increment attempt counter
      │     ├─ Check MAX_GENERATION_ATTEMPTS:
      │     │  ├─ If 0 (infinite retries): Loop back to Step 2
      │     │  │  with improvement instructions
      │     │  └─ If > 0 and attempts >= limit:
      │     │     └─ Return best content so far
      │     └─ Add reviewer feedback to improvement context
      │
      ├─ Step 5: SAVE & FEEDBACK
      │  │
      │  └─ FeedbackAgent.process()
      │     ├─ Save GeneratedContent to BD
      │     ├─ Register AgentDecisionRecords
      │     └─ Make content ready for teacher feedback
      │
      └─ Step 6: RETURN
         └─ Response {
            conversation_id,
            content_type,
            content,
            subject,
            topic,
            confidence,
            generation_attempts,
            ...
          }
```

### **Agent Responsibilities**

| Agente | Entrada | Proceso | Salida |
|--------|---------|---------|--------|
| **Analyzer** | user_prompt, subject?, topic?, doc_context? | Metadata detection (hybrid keyword+LLM), RAG retrieval, requirement extraction | {content_type, difficulty, retrieved_chunks, requirements} |
| **Generator** | analysis, subject, topic, level, rag_context, feedback_examples | Build enhanced prompt, Call LLM, Generate content | Generated content text |
| **Reviewer** | generated_content, requirements, difficulty | Validate quality, check requirements, score fidelity | {pass: bool, score: float, feedback: str, issues: []} |
| **Feedback** | GeneratedContent, FeedbackRecord | Extract learning patterns, update learning examples, track preferences | Updated learning database |

### **Vector Database (ChromaDB)**

```
User uploads document.pdf
      │
      ▼
DocumentIngestor.parse_file('pdf')
      ├─ PyMuPDF → extract all text
      └─ Return: full document text
      │
      ▼
SemanticChunker.chunk_text()
      ├─ Split by sentences
      ├─ Chunk size: 1500 chars
      ├─ Overlap: 12%
      └─ Create: [chunk1, chunk2, chunk3, ...]
      │
      ▼
VectorDatabaseService.add_documents()
      ├─ For each chunk:
      │  ├─ Embed using embedding model
      │  ├─ Store in ChromaDB
      │  └─ Return: vector_id
      └─ Create: chunk_ids = [id1, id2, ...]
      │
      ▼
Save to PostgreSQL:
      ├─ Document {
      │  id: uuid,
      │  filename, file_type,
      │  chunks_count,
      │  vector_index_ids: [id1, id2, ...] # JSON
      └─ }
         ├─ Chunk (multiple records) {
         │  document_id, chunk_index, text, vector_id
         └─ }
      │
      ▼
Later: User asks question
      │
      ▼
RAGService.retrieve(query, subject?, topic?, top_k=5)
      │
      ├─ Query ChromaDB for top_k*3 candidates
      ├─ Apply metadata filters (subject, topic)
      ├─ Re-rank candidates (keyword overlap + distance)
      └─ Return: top_k most relevant chunks
      │
      ▼
Send chunks to GeneratorAgent
      └─ Enhance prompt with retrieved context
```

### **LLM Service**

```
LLMService.generate_content(
  content_type='exam',
  subject='Biology',
  topic='Photosynthesis',
  level='university',
  additional_context=rag_chunks,
  previous_feedback=[]
)
      │
      ├─ if settings.LLM_PROVIDER == 'gemini':
      │  └─ Call GenerativeAI API (Gemini 1.5 Pro)
      │
      └─ elif settings.LLM_PROVIDER == 'openai':
         └─ Call OpenAI API (GPT-4o)
      │
      ▼
Response: Generated content text
      │
      └─ Stream option: generate_content_stream()
         └─ Yield chunks for streaming UI
```

---

## 🔐 6. AUTENTICACIÓN Y SEGURIDAD

### **JWT Token Flow**

```
Register
├─ POST /auth/register {email, password, name}
└─ Create User + hash password (passlib)

Login
├─ POST /auth/login {email, password}
├─ Verify password (passlib)
├─ Create JWT:
│  ├─ payload: {sub: user_id}
│  ├─ secret: settings.SECRET_KEY
│  ├─ algorithm: HS256
│  ├─ expires_in: 30 minutes
│  └─ Return: Bearer token
└─ Client stores in localStorage / cookies

Subsequent Requests
├─ Include: Authorization: Bearer {token}
├─ Backend:
│  ├─ Extract token from header
│  ├─ Decode with SECRET_KEY
│  ├─ Verify expiry
│  ├─ Extract user_id
│  └─ Check user owns resource
└─ Grant access or 401 Unauthorized
```

### **Security Implementations**

```
CORS (frontend/backend communication)
├─ Allowed origins: localhost:3000, localhost:8000
└─ Credentials mode: include

Password Security
├─ Hash: passlib (bcrypt-like)
├─ Verify on login
└─ Never store plaintext

User Isolation
├─ All endpoints verify user_id from token
├─ Conversations/Documents/Feedback scoped to user
└─ No cross-user data access possible

Token Expiry
├─ Access token: 30 minutes
├─ Expired: Return 401, frontend redirects to login
└─ Refresh: Not implemented (add for production)

Error Handling
├─ Return generic messages (no info leakage)
├─ Log details server-side
└─ Consistent error response format
```

---

## 📋 7. MODELOS DE DATOS (PYDANTIC SCHEMAS)

```python
# User Management
UserCreate = {email, password, name, institution?}
UserResponse = {id, email, name, institution, subject, level, is_active, created_at, updated_at}

# Authentication
TokenResponse = {access_token, token_type='bearer'}

# Conversations
ConversationCreate = {title, subject?, topic?}
ConversationResponse = {
  id, title, subject, topic,
  primary_subject?, primary_topic?,
  all_topics? (JSON),
  created_at, updated_at, last_edited?
}

# Messages
MessageRequest = {user_prompt, conversation_id?, document_id?, difficulty?}
MessageCreate = {role, content, content_type?}
MessageResponse = {
  id, role, content, timestamp,
  subject?, topic?,
  detected_content_type?, detection_confidence?, detection_method?,
  document_id?
}
RoutedMessageResponse = {
  conversation_id, is_new_conversation,
  subject?, topic?, content_type?,
  confidence, detection_method,
  content, title?
}

# Generated Content
GenerationRequest = {content_type, subject, topic, level}
GenerationResponse = {
  id, content_type, title, content,
  feedback?, version, created_at, updated_at,
  feedback_records[]
}

# Documents & Chunks
DocumentUpload = {subject, topic?, description?}
DocumentResponse = {id, filename, file_type, chunks_count, created_at, updated_at}
ChunkResponse = {id, document_id, text, chunk_index, vector_id}

# Feedback
FeedbackSubmit = {feedback, status, editor_name?}
FeedbackRecordResponse = {id, content_id, feedback, status, editor_name?, timestamp}
```

---

## ⚙️ 8. CONFIGURACIÓN

```python
# backend/app/core/config.py

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/academic_generator"

# JWT
SECRET_KEY = "your-secret-key-change-this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# LLM Providers
GOOGLE_API_KEY = "..." # Gemini
GEMINI_MODEL = "gemini-1.5-pro"
OPENAI_API_KEY = "..." # GPT-4o
GPT_MODEL = "gpt-4o"
LLM_PROVIDER = "gemini" # or "openai"

# Vector Database
CHROMA_DIR = "./chromadb_data"

# Document Processing
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_FILE_TYPES = ["pdf", "docx", "txt"]
CHUNK_SIZE = 1500  # characters
CHUNK_OVERLAP = 0.12  # 12%

# Generation
MAX_GENERATION_ATTEMPTS = 0  # 0 = infinite HITL retries
GENERATION_TIMEOUT = 60  # seconds

# App
APP_NAME = "Academic Content Generator"
DEBUG = False
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8000"]
```

---

## 📁 9. ESTRUCTURA DE ARCHIVOS IMPORTANTE

### **Backend** [backend/]

```
backend/
├── main.py (⭐ Entry point FastAPI)
├── requirements.txt (Dependencias)
├── pytest.ini (Config testing)
├── app/
│  ├── __init__.py
│  ├── main.py (Compatibility shim)
│  │
│  ├── api/ (⭐ ROUTERS)
│  │  ├── __init__.py (export routers)
│  │  ├── auth.py (Register, Login)
│  │  ├── conversations.py (CRUD + message generation)
│  │  ├── documents.py (Upload, RAG)
│  │  ├── feedback.py (Teacher feedback loop)
│  │  └── health.py (Health check)
│  │
│  ├── agents/ (⭐ MULTI-AGENT SYSTEM)
│  │  ├── analyzer_agent.py (Prompt analysis + metadata)
│  │  ├── generator_agent.py (Content generation)
│  │  ├── reviewer_agent.py (Quality validation)
│  │  ├── feedback_agent.py (Learning from feedback)
│  │  └── metadata_analyzer.py (Keyword + LLM detection)
│  │
│  ├── orchestration/ (⭐ WORKFLOW COORDINATOR)
│  │  └── content_orchestrator.py (Main pipeline: Analyze→Generate→Review→Loop→Return)
│  │
│  ├── services/ (⭐ BUSINESS LOGIC)
│  │  ├── conversation_service.py (CRUD conversations/messages)
│  │  ├── document_ingestion_service.py (Parse PDF/DOCX/TXT)
│  │  ├── vector_service.py (ChromaDB wrapper)
│  │  ├── rag_service.py (RAG retrieval + re-ranking)
│  │  ├── llm_service.py (Gemini / GPT-4o interface)
│  │  ├── user_service.py (User auth operations)
│  │  ├── feedback_learning_service.py (Learning loop)
│  │  └── content_service.py (Content CRUD)
│  │
│  ├── models/ (⭐ DATABASE MODELS)
│  │  └── models.py (SQLAlchemy: User, Conversation, Message, etc.)
│  │
│  ├── schemas/ (⭐ PYDANTIC SCHEMAS)
│  │  └── schemas.py (Request/Response validation)
│  │
│  ├── core/ (⭐ INFRASTRUCTURE)
│  │  ├── config.py (Settings)
│  │  ├── database.py (SQLAlchemy engine, sessions)
│  │  ├── security.py (JWT, password hashing)
│  │  └── logger.py (Logging setup)
│  │
│  └── middleware/ (⭐ HTTP MIDDLEWARE)
│     ├── cors_handler.py (CORS configuration)
│     └── error_handler.py (Exception handling)
│
├── tests/
│  ├── test_rag_integration.py
│  └── test_metadata_analyzer.py
```

### **Frontend** [frontend/]

```
frontend/
├── package.json (Dependencies: next, react, typescript, zustand, tailwind)
├── tsconfig.json (TypeScript config)
├── next.config.js|ts (Next.js config)
├── tailwind.config.js (Tailwind CSS config)
│
├── pages/ (⭐ NEXT.JS ROUTES)
│  ├── _app.tsx (App wrapper)
│  ├── index.tsx (Home / Main chat)
│  ├── dashboard.tsx (Overview + stats)
│  ├── login.tsx (Login form)
│  ├── register.tsx (Register form)
│  ├── documents.tsx (Document manager)
│  ├── settings.tsx (User settings)
│  └── conversations/
│     └── [id].tsx (Individual conversation)
│
├── components/ (⭐ REACT COMPONENTS)
│  ├── Layout.tsx (App wrapper)
│  ├── Sidebar.tsx (Conversation list)
│  ├── ChatWindow.tsx (Message display)
│  ├── ChatInput.tsx (User input)
│  ├── MessageItem.tsx (Message bubble)
│  ├── ContentEditor.tsx (Edit/preview)
│  ├── ContentPreview.tsx (Display content)
│  ├── DocumentUploader.tsx (Drag-drop upload)
│  ├── FeedbackPanel.tsx (Feedback form)
│  ├── RegenerationButton.tsx (Re-generate trigger)
│  └── ScrollArea.tsx (Scroll wrapper)
│
├── hooks/ (⭐ CUSTOM HOOKS)
│  ├── useApi.ts (API methods wrapper)
│  ├── useConversations.ts (Conversation CRUD)
│  ├── useDocuments.ts (Document operations)
│  ├── useContentGeneration.ts (Generate content)
│  └── useFeedback.ts (Submit feedback)
│
├── store/ (⭐ GLOBAL STATE)
│  └── appStore.ts (Zustand: conversations, messages, documents, UI state)
│
├── lib/ (⭐ UTILITIES)
│  └── api.ts (Axios instance, request methods)
│
├── types/ (⭐ TYPESCRIPT TYPES)
│  └── index.ts (User, Conversation, Message, etc.)
│
├── styles/
│  └── globals.css (Tailwind + global styles)
│
└── public/ (Static assets)
```

---

## 🔄 10. FLUJOS CLAVE

### **Flujo: Usuario crea conversación y envía mensaje**

```
1. User clicks "New Chat" en Sidebar
   └─ ChatInput visible

2. User types: "Create an exam about photosynthesis"
   ├─ handleSendMessage() triggered
   ├─ Create tempUserMessage {role: 'user', content: '...'}
   ├─ Add to store
   └─ Clear input

3. POST /conversations/{id}/messages
   ├─ Backend:
   │  ├─ MetadataAnalyzer
   │  │  ├─ Keyword match: "photosynthesis" → Biology/Photosynthesis
   │  │  ├─ Keyword match: "exam" → content_type='exam'
   │  │  └─ Return: {subject:'Biology', topic:'Photosynthesis', content_type:'exam', confidence:1.0}
   │  │
   │  ├─ ContentOrchestrator.generate_with_rag_and_agents()
   │  │  ├─ AnalyzerAgent: Extract requirements, RAG search (si doc)
   │  │  ├─ GeneratorAgent: Build prompt + call Gemini
   │  │  ├─ ReviewerAgent: Validate content
   │  │  ├─ Loop if needed (HITL)
   │  │  └─ Save GeneratedContent to BD
   │  │
   │  └─ Return RoutedMessageResponse {conversation_id, content, subject, topic, ...}

4. Frontend:
   ├─ Receive response
   ├─ Create assistantMessage {role: 'assistant', content: response.content}
   ├─ addMessage(conversationId, assistantMessage)
   ├─ Update store
   └─ ChatWindow re-renders + scrolls to bottom

5. User sees:
   ├─ Own message: "Create an exam about photosynthesis"
   └─ AI response: [Generated exam content]
```

### **Flujo: Usuario sube documento para RAG**

```
1. User accede a documents.tsx
   └─ DocumentUploader component

2. User drag-drops file: "biology_notes.pdf"
   ├─ File validation: type=pdf ✓, size<50MB ✓
   └─ Subject/Topic inputs: Biology / Photosynthesis

3. POST /documents/upload
   ├─ Backend:
   │  ├─ DocumentIngestor.parse_file()
   │  │  └─ PyMuPDF: extract all text from PDF
   │  │
   │  ├─ SemanticChunker.chunk_text()
   │  │  ├─ Split by sentences
   │  │  ├─ Chunk size: 1500 chars, overlap: 12%
   │  │  └─ Create: [chunk1, chunk2, chunk3, ...]
   │  │
   │  ├─ VectorDatabaseService.add_documents()
   │  │  ├─ Embed each chunk
   │  │  ├─ Store in ChromaDB
   │  │  └─ Get: [vector_id1, vector_id2, ...]
   │  │
   │  └─ PostgreSQL:
   │     ├─ Document {id, filename, chunks_count, vector_index_ids}
   │     └─ Chunk[] {document_id, text, chunk_index, vector_id}

4. Frontend:
   ├─ Display: "Document uploaded successfully"
   ├─ Add to documents[] in store
   └─ Now available for RAG in future generations

5. Future message in same conversation:
   ├─ User: "Create an exam from the uploaded notes"
   ├─ AnalyzerAgent:
   │  ├─ Detect: document_id in request
   │  └─ RAGService.retrieve(query, top_k=5)
   │     ├─ ChromaDB semantic search
   │     └─ Return: top relevant chunks from PDF
   │
   ├─ GeneratorAgent:
   │  ├─ Build prompt with RAG context
   │  └─ "...additional context from teacher notes: [chunks]..."
   │
   └─ LLM generates content informed by document
```

### **Flujo: Teacher feedback loop (HITL)**

```
1. User sees generated exam
   ├─ Content displayed in ContentPreview
   └─ FeedbackPanel visible below

2. Teacher reviews exam:
   ├─ Reads content
   ├─ Finds: Questions too difficult
   └─ Clicks FeedbackPanel

3. Teacher submits feedback:
   ├─ Textarea: "Questions should be more basic for secondary level"
   ├─ Status: needs_revision
   ├─ Editor name: "John Doe"
   └─ Click "Submit Feedback"

4. POST /feedback/{content_id}
   ├─ Backend:
   │  ├─ Save FeedbackRecord {content_id, feedback, status='needs_revision', editor_name}
   │  │
   │  ├─ Trigger regeneration:
   │  │  ├─ Extract content_type, subject, topic from GeneratedContent
   │  │  ├─ Add feedback to context:
   │  │  │  "Previous feedback: Questions too difficult...
   │  │  │   Please regenerate with simpler questions."
   │  │  │
   │  │  └─ ContentOrchestrator.generate_with_rag_and_agents()
   │  │     ├─ Same pipeline as before
   │  │     ├─ But with feedback in context
   │  │     └─ Increment GeneratedContent.total_regeneration_attempts
   │  │
   │  └─ If feedback.status='approved':
   │     ├─ Save as learning example
   │     └─ Future few-shot prompts incluirá este ejemplo

5. Frontend:
   ├─ Display: "Feedback submitted"
   ├─ New content regenerated with feedback
   └─ User sees updated exam (easier questions)

6. Loop:
   ├─ Teacher reviews again
   ├─ Can submit feedback again (infinite retries)
   └─ Process continues until 'approved'
```

---

## 📊 11. ESTADÍSTICAS DEL PROYECTO

| Métrica | Valor |
|---------|-------|
| **Total Modelos SQLAlchemy** | 8 (User, Conversation, Message, GeneratedContent, FeedbackRecord, Document, Chunk, AgentDecisionRecord) |
| **Total Endpoints FastAPI** | 18+ (auth, conversations, documents, feedback, health) |
| **Total Componentes React** | 12+ (ChatWindow, ChatInput, Sidebar, MessageItem, etc.) |
| **Agentes IA** | 4 (Analyzer, Generator, Reviewer, Feedback) |
| **Métodos de autenticación** | 1 (JWT Bearer) |
| **Proveedores LLM** | 2 (Gemini 1.5 Pro, GPT-4o) |
| **Vector DB** | 1 (ChromaDB) |
| **Formatos documento soportados** | 3 (PDF, DOCX, TXT) |
| **Content types generados** | 5 (exam, slideshow, guide, question, text) |
| **Áreas académicas** | 8 (Biology, Chemistry, Physics, Mathematics, History, Literature, Geography, Economics) |
| **Nivel máximo HITL retries** | ∞ (configurable a N) |

---

## ✅ CONCLUSIONES

Este es un **sistema completo y escalable** para generación de contenido académico con:

1. ✅ **Arquitectura modular**: Separación clara entre API, servicios, agentes, BD
2. ✅ **Multi-agente IA**: Pipeline completo Analyze→Generate→Review→Loop
3. ✅ **RAG avanzado**: Búsqueda semántica + re-ranking + contexto docente
4. ✅ **Aprendizaje humano**: Feedback loop infinito con guardia de ejemplos
5. ✅ **Conversaciones persistentes**: Historial completo con metadata auto-detectada
6. ✅ **UI moderna**: Next.js + React + Tailwind con estado global (Zustand)
7. ✅ **Security**: JWT + user isolation + role-based data access
8. ✅ **Extensible**: Fácil agregar nuevos agentes, content types, LLM providers

**Tiempo estimado desarrollo:** 3-4 meses (full-stack con testing, deployment)
