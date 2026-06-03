import { create } from 'zustand';
import { ConversationThread, Message, GeneratedContent, Document, ChunkResponse, Folder } from '@/types';
import { Lang } from '@/lib/translations';

interface AppStore {
  // User state
  currentUser: any | null;
  setCurrentUser: (user: any) => void;

  // Folder state
  folders: Folder[];
  setFolders: (folders: Folder[]) => void;
  addFolder: (folder: Folder) => void;
  updateFolder: (id: string, updates: Partial<Folder>) => void;
  removeFolder: (id: string) => void;

  // Conversation state
  conversations: ConversationThread[];
  currentConversation: ConversationThread | null;
  setConversations: (conversations: ConversationThread[]) => void;
  setCurrentConversation: (conversation: ConversationThread | null) => void;
  addConversation: (conversation: ConversationThread) => void;
  updateConversation: (id: string, updates: Partial<ConversationThread>) => void;
  removeConversation: (id: string) => void;

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

  // Language preference (persisted to localStorage)
  language: Lang;
  setLanguage: (lang: Lang) => void;

  // Dark mode preference (persisted to localStorage)
  darkMode: boolean;
  setDarkMode: (on: boolean) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  currentUser: null,
  setCurrentUser: (user) => set({ currentUser: user }),

  // Folders
  folders: [],
  setFolders: (folders) => set({ folders }),
  addFolder: (folder) =>
    set((state) => ({ folders: [...state.folders, folder] })),
  updateFolder: (id, updates) =>
    set((state) => ({
      folders: state.folders.map((f) => (f.id === id ? { ...f, ...updates } : f)),
    })),
  removeFolder: (id) =>
    set((state) => ({ folders: state.folders.filter((f) => f.id !== id) })),

  // Conversations
  conversations: [],
  currentConversation: null,
  setConversations: (conversations) => set({ conversations }),
  setCurrentConversation: (currentConversation) => set({ currentConversation }),
  addConversation: (conversation) =>
    set((state) => ({ conversations: [conversation, ...state.conversations] })),
  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
      currentConversation: state.currentConversation?.id === id
        ? { ...state.currentConversation, ...updates }
        : state.currentConversation,
    })),
  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      currentConversation: state.currentConversation?.id === id ? null : state.currentConversation,
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

  // Language preference — read initial value from localStorage (SSR-safe)
  language: (typeof window !== 'undefined'
    ? (localStorage.getItem('app_language') as Lang | null) ?? 'en'
    : 'en'),
  setLanguage: (lang) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('app_language', lang);
    }
    set({ language: lang });
  },

  // Dark mode — read from localStorage and sync the <html> class on init
  darkMode: (() => {
    if (typeof window === 'undefined') return false;
    const on = localStorage.getItem('darkMode') === 'true';
    if (on) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
    return on;
  })(),
  setDarkMode: (on) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('darkMode', String(on));
      if (on) document.documentElement.classList.add('dark');
      else document.documentElement.classList.remove('dark');
    }
    set({ darkMode: on });
  },
}));
