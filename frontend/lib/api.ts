import axios, { AxiosError } from 'axios';
import {
  LLMRequest,
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

// Public paths that don't require authentication
const PUBLIC_PATHS = ['/auth/login', '/auth/register'];

// Request interceptor: attach token; redirect to login if missing on protected routes
api.interceptors.request.use((config) => {
  if (typeof window === 'undefined') return config;
  const token = localStorage.getItem('token');
  const isPublic = PUBLIC_PATHS.some((p) => config.url?.includes(p));
  if (!token && !isPublic) {
    // Cancel request and redirect — no unauthenticated API calls
    window.location.href = '/login';
    return Promise.reject(new Error('Not authenticated'));
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: redirect to login on 401 (session expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const apiClient = {
  // Auth endpoints
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  register: (email: string, password: string, name: string) =>
    api.post('/auth/register', { email, password, name }),

  getMe: () => api.get('/auth/me'),

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
    if (request.subject) formData.append('subject', request.subject);
    if (request.description) formData.append('description', request.description);

    // Use bare axios (not the api instance) so the application/json Content-Type
    // default is NOT present — the browser then sets multipart/form-data with the
    // correct boundary automatically. Authorization is added manually.
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    return axios.post(`${API_URL}/documents/upload`, formData, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  },

  uploadFromUrl: (url: string, request: DocumentUploadRequest): Promise<{ data: DocumentUploadResponse }> =>
    api.post('/documents/fetch-url', { url, ...request }),

  // Regenerate content with teacher feedback (infinite HITL retries)
  regenerateContent: (conversationId: string, contentId: string, feedbackText: string) =>
    api.post(`/conversations/${conversationId}/regenerate`, {
      content_id: contentId,
      feedback_text: feedbackText,
    }),

  // Submit feedback on generated content (standalone endpoint)
  submitContentFeedback: (
    contentId: string,
    feedback: string,
    status: 'approved' | 'needs_revision' | 'rejected',
    editorName?: string,
  ) =>
    api.post(`/feedback/${contentId}`, { feedback, status, editor_name: editorName }),

  // Fetch chunks for a document (for debugging RAG)
  getDocumentChunks: (documentId: string) =>
    api.get(`/documents/${documentId}/chunks`),

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

  // ── HITL: message rating (thumbs up only now) ───────────────────────────
  rateMessage: (
    conversationId: string,
    messageId: string,
    rating: 1 | -1,
    feedbackText?: string,
  ) =>
    api.post(`/conversations/${conversationId}/messages/${messageId}/rate`, {
      rating,
      feedback_text: feedbackText ?? null,
    }),

  // ── HITL: professor edits output → LLM produces refined version ──────────
  refineMessage: (
    conversationId: string,
    messageId: string,
    editedContent: string,
  ) =>
    api.post(`/conversations/${conversationId}/messages/${messageId}/refine`, {
      edited_content: editedContent,
    }),

  // ── HITL: classification correction ─────────────────────────────────────
  reclassifyConversation: (
    conversationId: string,
    subject: string,
    folderId?: string | null,
  ) =>
    api.patch(`/conversations/${conversationId}/reclassify`, {
      subject,
      folder_id: folderId ?? null,
    }),

  // Folder management endpoints
  getFolders: () => api.get('/folders'),
  getFolder: (folderId: string) => api.get(`/folders/${folderId}`),
  createFolder: (data: any) => api.post('/folders', data),
  updateFolder: (folderId: string, data: any) => api.put(`/folders/${folderId}`, data),
  deleteFolder: (folderId: string) => api.delete(`/folders/${folderId}`),
  getFolderConversations: (folderId: string) => api.get(`/folders/${folderId}/conversations`),
  moveConversationToFolder: (conversationId: string, folderId: string | null) =>
    api.post(`/conversations/${conversationId}/move-folder`, { folder_id: folderId }),

  // ── Audit trail ──────────────────────────────────────────────────────────
  getAuditTrail: (conversationId: string) =>
    api.get(`/conversations/${conversationId}/audit`),

  // ── Evaluation (RAGAS) ───────────────────────────────────────────────────
  evaluateConversation: (conversationId: string) =>
    api.get(`/conversations/${conversationId}/evaluate`),

  // ── Export ───────────────────────────────────────────────────────────────
  exportMessage: (conversationId: string, messageId: string, format: 'pdf' | 'docx') => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    // Use window.open for file download to avoid binary blob handling issues
    const url = `${API_URL}/conversations/${conversationId}/messages/${messageId}/export?format=${format}`;
    const a = document.createElement('a');
    a.href = url;
    a.setAttribute('download', '');
    // We need Authorization — use fetch + blob
    return fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => {
        if (!r.ok) throw new Error('Export failed');
        return r.blob();
      })
      .then((blob) => {
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = `export.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(blobUrl);
      });
  },

  // ── Question bank ─────────────────────────────────────────────────────────
  listQuestions: (params?: { subject?: string; topic?: string; bloom_level?: string; q?: string }) =>
    api.get('/questions', { params }),
  createQuestion: (data: any) => api.post('/questions', data),
  updateQuestion: (id: string, data: any) => api.put(`/questions/${id}`, data),
  deleteQuestion: (id: string) => api.delete(`/questions/${id}`),
  extractQuestionsFromMessage: (messageId: string) =>
    api.post(`/questions/extract/${messageId}`),

  // ── Structured syllabus input ─────────────────────────────────────────────
  uploadSyllabus: (data: {
    course_name: string;
    subject: string;
    week?: number;
    learning_objectives?: string[];
    topics?: Array<{ name: string; bloom_level?: string }>;
    notes?: string;
  }) => api.post('/documents/syllabus', data),

  // ── Streaming message (SSE) ───────────────────────────────────────────────
  /**
   * Send a message and receive the response as a ReadableStream of SSE events.
   * The caller iterates with an async generator or reads the stream manually.
   */
  sendMessageStream: async function* (request: {
    userPrompt: string;
    conversationId?: string | null;
    documentId?: string | null;
    difficulty?: string | null;
  }) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const resp = await fetch(`${API_URL}/conversations/message/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        user_prompt: request.userPrompt,
        conversation_id: request.conversationId ?? null,
        document_id: request.documentId ?? null,
        difficulty: request.difficulty ?? null,
      }),
    });

    if (!resp.ok) throw new Error(`Stream failed: ${resp.status}`);
    if (!resp.body) throw new Error('No response body');

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const raw = line.slice(6).trim();
          if (raw) {
            try {
              yield JSON.parse(raw);
            } catch {
              // skip malformed
            }
          }
        }
      }
    }
  },
};

export type ApiError = AxiosError<{ detail?: string }>;
