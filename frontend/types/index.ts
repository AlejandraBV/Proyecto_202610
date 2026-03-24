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
  subject: string;
  level: string;
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
  subject: string;
  level: string;
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
}

