// Types for academic content generator

export type ContentType = 'exam' | 'slideshow' | 'guide' | 'question' | 'text';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  institution: string;
  subject: string;
  level: 'elementary' | 'secondary' | 'university' | 'professional';
  createdAt: string;
  updatedAt: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  contentType?: ContentType;
  retrievedChunks?: ChunkResponse[]; // Chunks used for generation
  agentDecisions?: AgentDecisionResponse[]; // Agent decision audit trail
  // Auto-detected metadata
  subject?: string;
  topic?: string;
  detectedContentType?: string;
  detectionConfidence?: number;
  detectionMethod?: 'keywords' | 'llm' | 'document';
  // Document attachment (for user messages that included a file)
  documentId?: string;
  documentName?: string;
  // Bloom's taxonomy distribution (assistant messages)
  bloomTags?: BloomTag[];
}

export interface ConversationThread {
  id: string;
  userId: string;
  title: string;
  subject: string;
  topic: string;
  // Auto-detected primary subject/topic
  primarySubject?: string;
  primaryTopic?: string;
  allTopics?: string; // JSON list of all topics discussed
  folderId?: string | null; // Folder the conversation belongs to
  messages: Message[];
  generatedContent: GeneratedContent[];
  documents: Document[]; // Associated documents
  createdAt: string;
  updatedAt: string;
  lastEdited?: string;
}

export interface GeneratedContent {
  id: string;
  conversationId: string;
  contentType: ContentType;
  title: string;
  content: string;
  feedback?: string;
  version: number;
  feedback_history: FeedbackRecord[];
  documentIds?: string[]; // Source documents used
  retrievedChunks?: ChunkResponse[]; // Chunks retrieved for generation
  agentDecisions?: AgentDecisionResponse[]; // Agent decisions audit trail
  iterations?: number; // Number of re-ranking iterations
  confidenceScore?: number; // Final confidence score
  createdAt: string;
  updatedAt: string;
}

export interface FeedbackRecord {
  id: string;
  contentId: string;
  feedback: string;
  status: 'approved' | 'needs_revision' | 'rejected';
  timestamp: string;
  editorName: string;
}

export interface VectorDocument {
  id: string;
  contentId: string;
  content: string;
  embedding: number[];
  metadata: Record<string, any>;
}

// New RAG-related types
export interface Document {
  id: string;
  userId: string;
  conversationId?: string;
  filename: string;
  fileType: 'pdf' | 'docx' | 'txt';
  originalContent: string;
  source: 'pdf_upload' | 'docx_upload' | 'url_fetch' | 'direct_text';
  url?: string; // If fetched from URL
  processed: boolean;
  subject?: string;
  createdAt: string;
  updatedAt: string;
  chunks?: ChunkResponse[];
}

export interface ChunkResponse {
  chunkIndex: number;
  text: string;
  chunkSize: number;
  overlapInfo: Record<string, any>;
  similarityScore?: number;
  documentId?: string;
  sourceFile?: string;
}

export interface AgentDecisionResponse {
  agentName: 'analyzer' | 'generator' | 'reviewer' | 'feedback';
  decision: 'approved' | 'needs_revision' | 'regenerate';
  reasoning: string;
  metadata: Record<string, any>;
  timestamp: string;
}

export interface DocumentUploadRequest {
  subject?: string;
  description?: string;
}

export interface DocumentUploadResponse {
  documentId: string;
  chunksCount: number;
  status: 'processed' | 'processing' | 'failed';
  message: string;
}

export interface SemanticSearchRequest {
  query: string;
  subject?: string;
  level?: string;
  limit?: number;
}

export interface SemanticSearchResponse {
  chunks: ChunkResponse[];
  totalFound: number;
  query: string;
}

export interface LLMRequest {
  contentType: ContentType;
  subject: string;
  topic: string;
  level: string;
  additionalContext?: string;
  previousFeedback?: string;
}

export interface LLMRequestWithContext extends LLMRequest {
  prompt: string;
  retrievedContext: ChunkResponse[];
  fewShotExamples?: Array<{
    input: string;
    output: string;
    feedback?: string;
  }>;
}

export interface RLMResponse {
  content: string;
  contentType: ContentType;
  suggestedTitle: string;
  confidence: number;
  agentDecisions: AgentDecisionResponse[];
  retrievedDocuments: string[];
  iterations: number;
  confidenceScore: number;
  retrievedChunks: ChunkResponse[];
}

export interface LLMResponse {
  generatedContent: string;
  contentType: ContentType;
  suggestedTitle: string;
  confidence: number;
}

// Intelligent message routing – auto topic detection
export interface MessageRequest {
  userPrompt: string;
  conversationId?: string | null;
  documentId?: string | null;
  difficulty?: string | null;
}

export interface DetectedMetadata {
  subject?: string | null;
  topic?: string | null;
  contentType?: string | null;
  confidence: number;
  detectionMethod?: 'keywords' | 'llm' | 'document' | null;
}

export interface RoutedMessageResponse {
  conversationId: string;
  isNewConversation: boolean;
  subject?: string | null;
  topic?: string | null;
  contentType?: string | null;
  confidence: number;
  detectionMethod?: string | null;
  content: string;
  title?: string | null;
  bloomTags?: BloomTag[] | null;
}

// New types for Folders and Topic Organization
export interface Folder {
  id: string;
  userId: string;
  name: string;
  description?: string;
  color: string;  // Hex color
  icon: string;   // emoji or icon name
  order: number;
  isDefault: boolean;
  conversationCount?: number;  // For UI display
  createdAt: string;
  updatedAt: string;
}

export interface FolderCreate {
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  isDefault?: boolean;
}

export interface FolderUpdate {
  name?: string;
  description?: string;
  color?: string;
  icon?: string;
  order?: number;
  isDefault?: boolean;
}

// Enhanced Conversation with Folder support
export interface ConversationWithFolder extends ConversationThread {
  folderId?: string;
  folder?: Folder;
  lockedTopic?: string;  // Topic locked to detect changes
  topicChangeHistory?: TopicChangeLog[];
}

// Topic change detection
export interface TopicChangeLog {
  id: string;
  conversationId: string;
  oldTopic?: string;
  newTopic: string;
  detectionConfidence: number;
  messageId?: string;
  automaticNewChatCreated: boolean;
  newChatId?: string;
  timestamp: string;
}

export interface TopicChangeEvent {
  oldTopic?: string;
  newTopic: string;
  confidence: number;
  newConversationId?: string;
  messageThatTriggeredChange: string;
}

// ── Bloom's Taxonomy ─────────────────────────────────────────────────────────

export interface BloomTag {
  level: 'Remember' | 'Understand' | 'Apply' | 'Analyze' | 'Evaluate' | 'Create';
  count: number;
  color: string; // tailwind color name: "green", "blue", "yellow", "orange", "red", "purple"
}

// ── Streaming ─────────────────────────────────────────────────────────────────

export type StreamEvent =
  | { type: 'meta'; conversation_id: string; is_new_conversation: boolean; subject: string; topic: string }
  | { type: 'chunk'; content: string }
  | { type: 'done'; message_id: string; conversation_id: string; bloom_tags: BloomTag[]; title: string }
  | { type: 'error'; message: string };

// ── Audit trail ───────────────────────────────────────────────────────────────

export type AuditEventType = 'message_rating' | 'reclassification' | 'agent_decision' | 'refinement';

export interface AuditEvent {
  type: AuditEventType;
  timestamp: string;
  // rating events
  message_id?: string;
  rating?: number;
  feedback_text?: string;
  // reclassification events
  original_subject?: string;
  corrected_subject?: string;
  sample_prompt?: string;
  // agent decision events
  agent_name?: string;
  decision?: string;
  reasoning?: string;
  quality_score?: number;
  iteration?: number;
  // refinement events
  content_preview?: string;
}

// ── Evaluation (RAGAS) ────────────────────────────────────────────────────────

export interface EvaluationTurn {
  message_id: string;
  user_query_preview: string;
  response_preview: string;
  faithfulness: number;
  answer_relevance: number;
  context_precision: number;
  overall: number;
}

export interface EvaluationResult {
  conversation_id: string;
  turns: EvaluationTurn[];
  averages: {
    faithfulness: number;
    answer_relevance: number;
    context_precision: number;
    overall: number;
  };
}

// ── Question bank ─────────────────────────────────────────────────────────────

export interface Question {
  id: string;
  content: string;
  answer?: string;
  question_type?: string;
  subject?: string;
  topic?: string;
  bloom_level?: string;
  difficulty?: string;
  tags?: string[];
  times_used: number;
  source_conversation_id?: string;
  source_message_id?: string;
  created_at: string;
  updated_at: string;
}

export interface QuestionCreate {
  content: string;
  answer?: string;
  question_type?: string;
  subject?: string;
  topic?: string;
  bloom_level?: string;
  difficulty?: string;
  tags?: string[];
  source_conversation_id?: string;
  source_message_id?: string;
}

// ── HITL (Human-in-the-Loop) types ──────────────────────────────────────────

export interface MessageRateRequest {
  rating: 1 | -1;         // +1 = helpful, -1 = not helpful
  feedbackText?: string;  // optional explanation for thumbs-down
}

export interface MessageRateResponse {
  ratingId: string;
  messageId: string;
  rating: 1 | -1;
  recorded: boolean;
}

export interface ReclassifyRequest {
  subject: string;         // user-corrected subject
  folderId?: string | null; // explicit folder; backend auto-resolves if omitted
}

export interface ReclassifyResponse {
  conversationId: string;
  oldSubject?: string | null;
  newSubject: string;
  folderId?: string | null;
  title: string;
}

// Enhanced UI State with Folder support
export interface ChatUIStateWithFolders {
  conversations: ConversationWithFolder[];
  conversationsByFolder: Record<string, ConversationWithFolder[]>;
  folders: Folder[];
  activeFolder?: string;
  activeConversation?: string;
  messages: Message[];
  documents: Document[];
  isLoading: boolean;
  error?: string;
  showFolderDialog: boolean;
  showMoveDialog: boolean;
  selectedConversation?: ConversationWithFolder;
}

