import axios, { AxiosError } from 'axios';
import {
  LLMRequest,
  LLMResponse,
  DocumentUploadRequest,
  DocumentUploadResponse,
  SemanticSearchRequest,
  SemanticSearchResponse,
  LLMRequestWithContext,
  RLMResponse,
  MessageRequest,
  RoutedMessageResponse,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const apiClient = {
  // Auth endpoints
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  register: (email: string, password: string, name: string, institution: string) =>
    api.post('/auth/register', { email, password, name, institution }),

  // Conversations
  getConversations: () => api.get('/conversations'),
  getConversation: (id: string) => api.get(`/conversations/${id}`),
  createConversation: (data: any) => api.post('/conversations', data),
  updateConversation: (id: string, data: any) => api.put(`/conversations/${id}`, data),
  deleteConversation: (id: string) => api.delete(`/conversations/${id}`),

  /**
   * Send a message with automatic topic detection.
   * The backend runs the hybrid keyword+LLM analyzer and may auto-create a new
   * conversation when the topic changes.
   */
  sendMessage: (request: MessageRequest): Promise<{ data: RoutedMessageResponse }> =>
    api.post('/conversations/message', {
      user_prompt: request.userPrompt,
      conversation_id: request.conversationId ?? null,
      document_id: request.documentId ?? null,
      difficulty: request.difficulty ?? null,
    }),

  // Content generation (legacy)
  generateContent: (conversationId: string, request: LLMRequest) =>
    api.post(`/conversations/${conversationId}/generate`, request),

  // New RAG content generation
  generateContentWithRAG: (conversationId: string, request: LLMRequestWithContext): Promise<{ data: RLMResponse }> =>
    api.post(`/conversations/${conversationId}/generate`, request),

  // Streaming endpoint
  generateContentStream: (conversationId: string, request: LLMRequest) =>
    api.post(`/conversations/${conversationId}/generate-stream`, request, {
      responseType: 'stream',
    }),

  // Feedback
  submitFeedback: (contentId: string, feedback: string, status: 'approved' | 'needs_revision' | 'rejected') =>
    api.post(`/content/${contentId}/feedback`, { feedback, status }),

  // Document management endpoints
  uploadDocument: (file: File, request: DocumentUploadRequest): Promise<{ data: DocumentUploadResponse }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subject', request.subject);
    formData.append('level', request.level);
    if (request.description) {
      formData.append('description', request.description);
    }
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  uploadFromUrl: (url: string, request: DocumentUploadRequest): Promise<{ data: DocumentUploadResponse }> =>
    api.post('/documents/fetch-url', { url, ...request }),

  getDocumentChunks: (documentId: string) =>
    api.get(`/documents/chunks/${documentId}`),

  semanticSearch: (request: SemanticSearchRequest): Promise<{ data: SemanticSearchResponse }> =>
    api.post('/documents/search/semantic', request),

  // Legacy file upload (keep for compatibility)
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // Legacy search (keep for compatibility)
  searchVectorDB: (query: string, conversationId: string) =>
    api.post('/search', { query, conversationId }),
};

export type ApiError = AxiosError<{ detail?: string }>;
