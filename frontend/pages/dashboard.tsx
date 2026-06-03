/**
 * /dashboard - Teacher dashboard overview page.
 * Quick-stats bar + same chat interface as the index page.
 * Redirects to /login if not authenticated.
 */
import React, { useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { ChatWindow } from '@/components/ChatWindow';
import { ChatInput, PendingDocument } from '@/components/ChatInput';
import { useAppStore } from '@/store/appStore';
import { apiClient } from '@/lib/api';
import { BloomTag, ConversationThread, ContentType, DetectedMetadata, Folder } from '@/types';
import { useT } from '@/hooks/useT';
import { tr } from '@/lib/translations';
import { v4 as uuidv4 } from 'uuid';
import toast from 'react-hot-toast';
import { BookOpen, FileText, MessageSquare } from 'lucide-react';

const Dashboard: React.FC = () => {
  const router = useRouter();
  const T = useT();
  const [inputValue, setInputValue] = React.useState('');
  const [detectedMetadata, setDetectedMetadata] = React.useState<DetectedMetadata | null>(null);
  const [useStreaming, setUseStreaming] = React.useState(true);
  const [pendingDocument, setPendingDocument] = React.useState<PendingDocument | null>(null);
  // Tracks the in-progress streaming message ID so ChatWindow can show it
  const streamingMsgIdRef = useRef<string | null>(null);

  const {
    conversations,
    currentConversation,
    folders,
    setConversations,
    setCurrentConversation,
    addMessage,
    addConversation,
    updateConversation,
    removeConversation,
    setFolders,
    addFolder,
    removeFolder,
    documents,
    loading,
    setLoading,
  } = useAppStore();

  // Auth guard
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) router.push('/login');
  }, [router]);

  // Load data on mount
  useEffect(() => {
    const load = async () => {
      try {
        const [convsRes, foldersRes] = await Promise.all([
          apiClient.getConversations(),
          apiClient.getFolders(),
        ]);
        const convs: ConversationThread[] = convsRes.data.map((c: any) => ({
          id: c.id,
          userId: c.user_id ?? '',
          title: c.title,
          subject: c.subject ?? 'General',
          topic: c.topic ?? 'Untitled',
          primarySubject: c.primary_subject ?? c.subject,
          primaryTopic: c.primary_topic ?? c.topic,
          allTopics: c.all_topics,
          folderId: c.folder_id ?? null,
          messages: (c.messages ?? []).map((m: any) => ({
            id: m.id, role: m.role, content: m.content,
            timestamp: m.timestamp, contentType: m.content_type,
          })),
          generatedContent: c.generated_contents ?? [],
          documents: [],
          createdAt: c.created_at,
          updatedAt: c.updated_at,
          lastEdited: c.last_edited,
        }));
        const flds: Folder[] = foldersRes.data.map((f: any) => ({
          id: f.id, userId: f.user_id, name: f.name,
          description: f.description, color: f.color, icon: f.icon,
          order: f.order, isDefault: f.is_default,
          createdAt: f.created_at, updatedAt: f.updated_at,
        }));
        setConversations(convs);
        setFolders(flds);
      } catch { /* silent */ }
    };
    load();
  }, []);

  const totalContent = conversations.reduce((s, c) => s + c.generatedContent.length, 0);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleCreateFolder = async (name: string, color?: string) => {
    try {
      const res = await apiClient.createFolder({ name, color: color ?? '#3B82F6' });
      const f = res.data;
      addFolder({
        id: f.id, userId: f.user_id, name: f.name, description: f.description,
        color: f.color, icon: f.icon, order: f.order, isDefault: f.is_default,
        createdAt: f.created_at, updatedAt: f.updated_at,
      });
      toast.success(`${T(tr.dashboard.folderCreated)}: "${name}"`);
    } catch { toast.error(T(tr.dashboard.folderCreateErr)); }
  };

  const handleDeleteFolder = async (folderId: string) => {
    try {
      await apiClient.deleteFolder(folderId);
      removeFolder(folderId);
      conversations.filter((c) => c.folderId === folderId)
        .forEach((c) => updateConversation(c.id, { folderId: null }));
      toast.success(T(tr.dashboard.folderDeleted));
    } catch { toast.error(T(tr.dashboard.folderDeleteErr)); }
  };

  const handleMoveConversation = async (conversationId: string, folderId: string | null) => {
    try {
      await apiClient.moveConversationToFolder(conversationId, folderId);
      updateConversation(conversationId, { folderId });
      const dest = folderId ? folders.find((f) => f.id === folderId)?.name ?? 'folder' : T(tr.sidebar.uncategorized);
      toast.success(`${T(tr.dashboard.movedTo)} ${dest}`);
    } catch { toast.error(T(tr.dashboard.moveErr)); }
  };

  // Helper: (re-)fetch conversation list + folders from server
  const refreshConversations = async () => {
    const [convsRes, foldersRes] = await Promise.all([
      apiClient.getConversations(), apiClient.getFolders(),
    ]);
    const convs: ConversationThread[] = convsRes.data.map((c: any) => ({
      id: c.id, userId: c.user_id ?? '', title: c.title,
      subject: c.subject ?? 'General', topic: c.topic ?? 'Untitled',
      primarySubject: c.primary_subject ?? c.subject,
      primaryTopic: c.primary_topic ?? c.topic,
      allTopics: c.all_topics, folderId: c.folder_id ?? null,
      messages: (c.messages ?? []).map((m: any) => ({
        id: m.id, role: m.role, content: m.content,
        timestamp: m.timestamp, contentType: m.content_type,
      })),
      generatedContent: c.generated_contents ?? [],
      documents: [], createdAt: c.created_at, updatedAt: c.updated_at,
    }));
    setConversations(convs);
    setFolders(foldersRes.data.map((f: any) => ({
      id: f.id, userId: f.user_id, name: f.name, description: f.description,
      color: f.color, icon: f.icon, order: f.order, isDefault: f.is_default,
      createdAt: f.created_at, updatedAt: f.updated_at,
    })));
    return convs;
  };

  // ── Streaming send ─────────────────────────────────────────────────────────
  const handleSendMessageStream = async (prompt: string) => {
    setLoading(true);
    const docId = pendingDocument?.id ?? null;
    setPendingDocument(null);            // clear chip immediately on send
    const tempUserMsg = {
      id: uuidv4(), role: 'user' as const,
      content: prompt, timestamp: new Date().toISOString(),
    };
    // Optimistically add user message
    if (currentConversation) addMessage(currentConversation.id, tempUserMsg);

    // Placeholder for streaming assistant message
    const streamId = uuidv4();
    streamingMsgIdRef.current = streamId;
    let streamConversationId = currentConversation?.id ?? '';
    let isNewConv = false;
    let accContent = '';
    let finalBloomTags: BloomTag[] | undefined;

    try {
      for await (const event of apiClient.sendMessageStream({
        userPrompt: prompt,
        conversationId: currentConversation?.id ?? null,
        documentId: docId,
      })) {
        if (event.type === 'meta') {
          streamConversationId = event.conversation_id;
          isNewConv = event.is_new_conversation;
          // Add placeholder streaming message to store
          addMessage(streamConversationId, {
            id: streamId, role: 'assistant' as const,
            content: '', timestamp: new Date().toISOString(),
          });
        } else if (event.type === 'chunk') {
          accContent += event.content;
          // Read fresh state from Zustand to avoid stale-closure reads
          const liveConvs = useAppStore.getState().conversations;
          updateConversation(streamConversationId, {
            messages: liveConvs
              .find((c) => c.id === streamConversationId)
              ?.messages.map((m) =>
                m.id === streamId ? { ...m, content: accContent } : m
              ) ?? [],
          });
        } else if (event.type === 'done') {
          finalBloomTags = event.bloom_tags;
          // Replace placeholder with the final saved message
          const finalMsg = {
            id: event.message_id,
            role: 'assistant' as const,
            content: accContent,
            timestamp: new Date().toISOString(),
            bloomTags: finalBloomTags,
          };
          const liveConvs2 = useAppStore.getState().conversations;
          const conv = liveConvs2.find((c) => c.id === streamConversationId);
          if (conv) {
            const filtered = conv.messages.filter((m) => m.id !== streamId);
            updateConversation(streamConversationId, { messages: [...filtered, finalMsg] });
          }
        } else if (event.type === 'error') {
          toast.error('Generation error: ' + event.message);
          break;
        }
      }
    } catch { toast.error(T(tr.dashboard.sendErr)); }

    // Refresh sidebar if a new conversation was created
    if (isNewConv) {
      const convs = await refreshConversations();
      const newConv = convs.find((c) => c.id === streamConversationId);
      if (newConv) setCurrentConversation(newConv);
      if (currentConversation) {
        toast.success(`${T(tr.dashboard.topicChanged)} ${newConv?.subject ?? ''} – ${newConv?.topic ?? ''}`, { duration: 4000 });
      }
    }

    setLoading(false);
  };

  // ── Non-streaming send (fallback) ──────────────────────────────────────────
  const handleSendMessageNonStream = async (prompt: string) => {
    setLoading(true);
    const docId = pendingDocument?.id ?? null;
    setPendingDocument(null);            // clear chip immediately on send
    const tempUserMessage = {
      id: uuidv4(), role: 'user' as const,
      content: prompt, timestamp: new Date().toISOString(),
    };
    if (currentConversation) addMessage(currentConversation.id, tempUserMessage);

    try {
      const response = await apiClient.sendMessage({
        userPrompt: prompt, conversationId: currentConversation?.id ?? null,
        documentId: docId,
      });
      const raw = response.data as any;
      const data = {
        conversationId: raw.conversation_id,
        isNewConversation: raw.is_new_conversation,
        subject: raw.subject,
        topic: raw.topic,
        contentType: raw.content_type,
        confidence: raw.confidence,
        detectionMethod: raw.detection_method,
        content: raw.content,
        title: raw.title,
        bloomTags: raw.bloom_tags ?? null,
      };

      setDetectedMetadata({
        subject: data.subject, topic: data.topic,
        contentType: data.contentType, confidence: data.confidence,
        detectionMethod: data.detectionMethod as any,
      });

      if (data.isNewConversation) {
        const convs = await refreshConversations();
        const newConv = convs.find((c) => c.id === data.conversationId);
        if (newConv) setCurrentConversation(newConv);
        if (currentConversation) {
          toast.success(`${T(tr.dashboard.topicChanged)} ${data.subject} – ${data.topic}`, { duration: 4000 });
        }
      } else {
        addMessage(data.conversationId, {
          id: uuidv4(), role: 'assistant' as const,
          content: data.content, timestamp: new Date().toISOString(),
          contentType: (data.contentType as ContentType) || 'text',
          bloomTags: data.bloomTags ?? undefined,
        });
        if (data.subject && data.topic) {
          updateConversation(data.conversationId, {
            subject: data.subject, topic: data.topic,
            primarySubject: data.subject, primaryTopic: data.topic,
          });
        }
      }
    } catch { toast.error(T(tr.dashboard.sendErr)); }
    finally { setLoading(false); }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const prompt = inputValue;
    setInputValue('');
    if (useStreaming) {
      await handleSendMessageStream(prompt);
    } else {
      await handleSendMessageNonStream(prompt);
    }
  };

  return (
    <Layout
      sidebar={
        <Sidebar
          conversations={conversations}
          folders={folders}
          currentConversationId={currentConversation?.id || null}
          onSelectConversation={(id) => {
            setCurrentConversation(conversations.find((c) => c.id === id) || null);
            setDetectedMetadata(null);
          }}
          onDeleteConversation={async (id) => {
            try {
              await apiClient.deleteConversation(id);
              removeConversation(id);
              toast.success(T(tr.dashboard.chatDeleted));
            } catch { toast.error(T(tr.dashboard.chatDeleteErr)); }
          }}
          onNewConversation={() => { setCurrentConversation(null); setDetectedMetadata(null); }}
          onCreateFolder={handleCreateFolder}
          onDeleteFolder={handleDeleteFolder}
          onMoveConversation={handleMoveConversation}
          loading={loading}
        />
      }
    >
      {/* Stats bar */}
      <div className="flex gap-4 border-b border-gray-200 bg-gray-50 px-6 py-3 text-sm">
        <div className="flex items-center gap-2 text-gray-600">
          <MessageSquare className="h-4 w-4" />
          <span>{conversations.length} {conversations.length !== 1 ? T(tr.dashboard.conversations) : T(tr.dashboard.conversation)}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-600">
          <FileText className="h-4 w-4" />
          <span>{totalContent} {totalContent !== 1 ? T(tr.dashboard.contentItems) : T(tr.dashboard.contentItem)}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-600">
          <BookOpen className="h-4 w-4" />
          <span>{documents.length} {documents.length !== 1 ? T(tr.dashboard.documents) : T(tr.dashboard.document)}</span>
        </div>
      </div>

      <ChatWindow conversation={currentConversation} isLoading={loading} />
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSendMessage}
        disabled={loading}
        loading={loading}
        detectedMetadata={detectedMetadata}
        pendingDocument={pendingDocument}
        onDocumentUploaded={setPendingDocument}
        onClearDocument={() => setPendingDocument(null)}
      />
    </Layout>
  );
};

export default Dashboard;
