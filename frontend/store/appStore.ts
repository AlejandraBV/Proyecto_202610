import { create } from 'zustand';
import { ConversationThread, Message, GeneratedContent, Document, ChunkResponse } from '@/types';

interface AppStore {
  // User state
  currentUser: any | null;
  setCurrentUser: (user: any) => void;

  // Conversation state
  conversations: ConversationThread[];
  currentConversation: ConversationThread | null;
  setConversations: (conversations: ConversationThread[]) => void;
  setCurrentConversation: (conversation: ConversationThread | null) => void;
  addConversation: (conversation: ConversationThread) => void;
  updateConversation: (id: string, updates: Partial<ConversationThread>) => void;

  // Message state
  addMessage: (conversationId: string, message: Message) => void;
  updateMessages: (conversationId: string, messages: Message[]) => void;

  // Generated content state
  addGeneratedContent: (conversationId: string, content: GeneratedContent) => void;
  updateGeneratedContent: (id: string, updates: Partial<GeneratedContent>) => void;

  // Document state (RAG)
  documents: Document[];
  currentDocument: Document | null;
  setDocuments: (documents: Document[]) => void;
  addDocument: (document: Document) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;
  setCurrentDocument: (document: Document | null) => void;

  // Chunk state (for displaying retrieved chunks)
  retrievedChunks: ChunkResponse[];
  setRetrievedChunks: (chunks: ChunkResponse[]) => void;
  clearRetrievedChunks: () => void;

  // UI state
  loading: boolean;
  setLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;

  // RAG UI state
  showRetrievedChunks: boolean;
  setShowRetrievedChunks: (show: boolean) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  currentUser: null,
  setCurrentUser: (user) => set({ currentUser: user }),

  conversations: [],
  currentConversation: null,
  setConversations: (conversations) => set({ conversations }),
  setCurrentConversation: (currentConversation) => set({ currentConversation }),
  addConversation: (conversation) =>
    set((state) => ({ conversations: [...state.conversations, conversation] })),
  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
      currentConversation: state.currentConversation?.id === id
        ? { ...state.currentConversation, ...updates }
        : state.currentConversation,
    })),

  addMessage: (conversationId, message) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === conversationId ? { ...c, messages: [...c.messages, message] } : c
      ),
      currentConversation:
        state.currentConversation?.id === conversationId
          ? { ...state.currentConversation, messages: [...state.currentConversation.messages, message] }
          : state.currentConversation,
    })),

  updateMessages: (conversationId, messages) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === conversationId ? { ...c, messages } : c
      ),
      currentConversation:
        state.currentConversation?.id === conversationId
          ? { ...state.currentConversation, messages }
          : state.currentConversation,
    })),

  addGeneratedContent: (conversationId, content) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === conversationId
          ? { ...c, generatedContent: [...c.generatedContent, content] }
          : c
      ),
      currentConversation:
        state.currentConversation?.id === conversationId
          ? {
              ...state.currentConversation,
              generatedContent: [...state.currentConversation.generatedContent, content],
            }
          : state.currentConversation,
    })),

  updateGeneratedContent: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((c) => ({
        ...c,
        generatedContent: c.generatedContent.map((gc) => (gc.id === id ? { ...gc, ...updates } : gc)),
      })),
      currentConversation: state.currentConversation
        ? {
            ...state.currentConversation,
            generatedContent: state.currentConversation.generatedContent.map((gc) =>
              gc.id === id ? { ...gc, ...updates } : gc
            ),
          }
        : null,
    })),

  loading: false,
  setLoading: (loading) => set({ loading }),
  error: null,
  setError: (error) => set({ error }),

  // Document state
  documents: [],
  currentDocument: null,
  setDocuments: (documents) => set({ documents }),
  addDocument: (document) =>
    set((state) => ({ documents: [...state.documents, document] })),
  updateDocument: (id, updates) =>
    set((state) => ({
      documents: state.documents.map((d) =>
        d.id === id ? { ...d, ...updates } : d
      ),
      currentDocument: state.currentDocument?.id === id
        ? { ...state.currentDocument, ...updates }
        : state.currentDocument,
    })),
  setCurrentDocument: (currentDocument) => set({ currentDocument }),

  // Chunk state
  retrievedChunks: [],
  setRetrievedChunks: (retrievedChunks) => set({ retrievedChunks }),
  clearRetrievedChunks: () => set({ retrievedChunks: [] }),

  // RAG UI state
  showRetrievedChunks: false,
  setShowRetrievedChunks: (showRetrievedChunks) => set({ showRetrievedChunks }),
}));
