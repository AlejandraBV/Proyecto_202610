import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { ChatWindow } from '@/components/ChatWindow';
import { ChatInput, PendingDocument } from '@/components/ChatInput';
import { useAppStore } from '@/store/appStore';
import { apiClient } from '@/lib/api';
import { ConversationThread, ContentType, DetectedMetadata, Folder } from '@/types';
import { v4 as uuidv4 } from 'uuid';
import toast from 'react-hot-toast';

const Home: React.FC = () => {
  const router = useRouter();
  const [inputValue, setInputValue] = useState('');
  const [detectedMetadata, setDetectedMetadata] = useState<DetectedMetadata | null>(null);
  const [pendingDocument, setPendingDocument] = useState<PendingDocument | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState('');

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
    setCurrentUser,
    loading,
    setLoading,
  } = useAppStore();

  // ── Auth guard ────────────────────────────────────────────────────────────
  // Runs synchronously on mount; redirects before any content renders.
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.replace('/login');
    } else {
      setAuthChecked(true);
    }
  }, [router]);

  // ── Load conversations & folders on mount ─────────────────────────────────
  useEffect(() => {
    if (!authChecked) return;          // wait until auth confirmed

    const load = async () => {
      try {
        const [convsRes, foldersRes, meRes] = await Promise.all([
          apiClient.getConversations(),
          apiClient.getFolders(),
          apiClient.getMe().catch(() => null),
        ]);

        if (meRes) {
          setCurrentUser(meRes.data);
        }

        // Map backend snake_case → camelCase
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
            id: m.id,
            role: m.role,
            content: m.content,
            timestamp: m.timestamp,
            contentType: m.content_type,
            documentId: m.document_id ?? undefined,
            documentName: m.document_name ?? undefined,
          })),
          generatedContent: c.generated_contents ?? [],
          documents: [],
          createdAt: c.created_at,
          updatedAt: c.updated_at,
          lastEdited: c.last_edited,
        }));

        const flds: Folder[] = foldersRes.data.map((f: any) => ({
          id: f.id,
          userId: f.user_id,
          name: f.name,
          description: f.description,
          color: f.color,
          icon: f.icon,
          order: f.order,
          isDefault: f.is_default,
          createdAt: f.created_at,
          updatedAt: f.updated_at,
        }));

        setConversations(convs);
        setFolders(flds);
      } catch {
        // Not critical – user may not be logged in yet
      }
    };
    load();
  }, [authChecked]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleNewConversation = () => {
    setCurrentConversation(null);
    setDetectedMetadata(null);
    setPendingDocument(null);   // clear document when starting fresh
  };

  const handleSelectConversation = (id: string) => {
    const conv = conversations.find((c) => c.id === id);
    setCurrentConversation(conv || null);
    setDetectedMetadata(null);
    setPendingDocument(null);   // clear document when switching chats
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await apiClient.deleteConversation(id);
      removeConversation(id);
      toast.success('Chat deleted');
    } catch {
      toast.error('Failed to delete chat');
    }
  };

  const handleCreateFolder = async (name: string, color?: string) => {
    try {
      const res = await apiClient.createFolder({ name, color: color ?? '#3B82F6' });
      const f = res.data;
      addFolder({
        id: f.id,
        userId: f.user_id,
        name: f.name,
        description: f.description,
        color: f.color,
        icon: f.icon,
        order: f.order,
        isDefault: f.is_default,
        createdAt: f.created_at,
        updatedAt: f.updated_at,
      });
      toast.success(`Folder "${name}" created`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || '';
      if (detail.includes('already exists')) {
        toast.error(`A folder named "${name}" already exists — try a different name.`);
      } else {
        toast.error(detail || 'Failed to create folder');
      }
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    try {
      await apiClient.deleteFolder(folderId);
      removeFolder(folderId);
      // Move conversations that were in this folder to uncategorized
      conversations
        .filter((c) => c.folderId === folderId)
        .forEach((c) => updateConversation(c.id, { folderId: null }));
      toast.success('Folder deleted');
    } catch {
      toast.error('Failed to delete folder');
    }
  };

  const handleUpdateFolder = async (folderId: string, data: { color?: string; name?: string }) => {
    try {
      await apiClient.updateFolder(folderId, data);
      // Refresh folders from server
      const foldersRes = await apiClient.getFolders();
      const flds: Folder[] = foldersRes.data.map((f: any) => ({
        id: f.id,
        userId: f.user_id,
        name: f.name,
        description: f.description,
        color: f.color,
        icon: f.icon,
        order: f.order,
        isDefault: f.is_default,
        createdAt: f.created_at,
        updatedAt: f.updated_at,
      }));
      setFolders(flds);
    } catch {
      toast.error('Failed to update folder');
    }
  };

  const handleMoveConversation = async (conversationId: string, folderId: string | null) => {
    try {
      await apiClient.moveConversationToFolder(conversationId, folderId);
      updateConversation(conversationId, { folderId });
      const folderName = folderId ? folders.find((f) => f.id === folderId)?.name ?? 'folder' : 'Uncategorized';
      toast.success(`Moved to ${folderName}`);
    } catch {
      toast.error('Failed to move chat');
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const prompt = inputValue;
    const docId = pendingDocument?.id ?? null;
    const docName = pendingDocument?.filename ?? undefined;
    setInputValue('');
    setPendingDocument(null);    // clear chip as soon as the message is sent
    setLoading(true);

    // Optimistic user bubble
    const tempId = uuidv4();
    const tempUserMessage = {
      id: tempId,
      role: 'user' as const,
      content: prompt,
      timestamp: new Date().toISOString(),
      documentId: docId ?? undefined,
      documentName: docName,
    };
    if (currentConversation) {
      addMessage(currentConversation.id, tempUserMessage);
    }

    try {
      const response = await apiClient.sendMessage({
        userPrompt: prompt,
        conversationId: currentConversation?.id ?? null,
        documentId: docId,
      });
      // Backend returns snake_case; normalise here
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
      };

      setDetectedMetadata({
        subject: data.subject,
        topic: data.topic,
        contentType: data.contentType,
        confidence: data.confidence,
        detectionMethod: data.detectionMethod as any,
      });

      if (data.isNewConversation) {
        // Backend auto-created a new conversation (topic changed or no prior conv)
        // Re-fetch folders because the backend may have auto-created one
        const foldersRes = await apiClient.getFolders();
        const flds: Folder[] = foldersRes.data.map((f: any) => ({
          id: f.id,
          userId: f.user_id,
          name: f.name,
          description: f.description,
          color: f.color,
          icon: f.icon,
          order: f.order,
          isDefault: f.is_default,
          createdAt: f.created_at,
          updatedAt: f.updated_at,
        }));
        setFolders(flds);

        // Also re-fetch conversations to get the server-assigned folder_id
        const convsRes = await apiClient.getConversations();
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
            id: m.id,
            role: m.role,
            content: m.content,
            timestamp: m.timestamp,
            contentType: m.content_type,
            documentId: m.document_id ?? undefined,
            documentName: m.document_name ?? undefined,
          })),
          generatedContent: c.generated_contents ?? [],
          documents: [],
          createdAt: c.created_at,
          updatedAt: c.updated_at,
          lastEdited: c.last_edited,
        }));
        setConversations(convs);

        // Activate the new conversation and simulate typing for its first message
        const newConv = convs.find((c) => c.id === data.conversationId);
        if (newConv) {
          setCurrentConversation(newConv);
          // The last message in the new conv is the assistant reply — animate it
          const lastMsg = newConv.messages[newConv.messages.length - 1];
          if (lastMsg?.role === 'assistant' && lastMsg.content) {
            const fullText = lastMsg.content;
            const emptyMsg = { ...lastMsg, content: '' };
            const msgsWithoutLast = newConv.messages.slice(0, -1);
            updateConversation(newConv.id, { messages: [...msgsWithoutLast, emptyMsg] });
            setLoading(false);

            const CHARS_PER_FRAME = 18;
            let pos = 0;
            setStreamingMsgId(lastMsg.id);
            setStreamingText('');
            const step = () => {
              pos = Math.min(pos + CHARS_PER_FRAME, fullText.length);
              setStreamingText(fullText.slice(0, pos));
              if (pos < fullText.length) {
                requestAnimationFrame(step);
              } else {
                updateConversation(newConv.id, {
                  messages: [...msgsWithoutLast, { ...lastMsg, content: fullText }],
                });
                setStreamingMsgId(null);
                setStreamingText('');
              }
            };
            requestAnimationFrame(step);
          }
        }

        const wasTopicChange = !!currentConversation;
        if (wasTopicChange) {
          toast.success(
            `Topic changed → new chat: ${data.subject ?? 'General'} – ${data.topic ?? 'Untitled'}`,
            { duration: 4000 }
          );
        }
      } else {
        // Same conversation – append assistant reply with typing animation
        const assistantMsgId = uuidv4();
        addMessage(data.conversationId, {
          id: assistantMsgId,
          role: 'assistant' as const,
          content: '',
          timestamp: new Date().toISOString(),
          contentType: (data.contentType as ContentType) || 'text',
        });
        updateConversation(data.conversationId, {
          ...(data.title ? { title: data.title } : {}),
          ...(data.subject ? { subject: data.subject, primarySubject: data.subject } : {}),
          ...(data.topic ? { topic: data.topic, primaryTopic: data.topic } : {}),
        });

        setLoading(false);

        // Reveal text via requestAnimationFrame — each frame is a new browser task
        // so React flushes the state update before the next frame, giving true streaming.
        const fullText: string = data.content ?? '';
        const CHARS_PER_FRAME = 18;
        let pos = 0;
        setStreamingMsgId(assistantMsgId);
        setStreamingText('');

        const step = () => {
          pos = Math.min(pos + CHARS_PER_FRAME, fullText.length);
          setStreamingText(fullText.slice(0, pos));
          if (pos < fullText.length) {
            requestAnimationFrame(step);
          } else {
            // Done — commit to Zustand and clear streaming state
            updateConversation(data.conversationId, {
              messages: useAppStore.getState()
                .conversations.find((c) => c.id === data.conversationId)
                ?.messages.map((m) =>
                  m.id === assistantMsgId ? { ...m, content: fullText } : m
                ) ?? [],
            });
            setStreamingMsgId(null);
            setStreamingText('');
          }
        };
        requestAnimationFrame(step);
        return; // setLoading(false) already called above
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to send message';
      toast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  // Don't render anything until auth is confirmed (avoids flash of home page
  // when no token is present — router.replace('/login') will fire in useEffect)
  if (!authChecked) return null;

  return (
    <Layout
      sidebar={
        <Sidebar
          conversations={conversations}
          folders={folders}
          currentConversationId={currentConversation?.id || null}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          onNewConversation={handleNewConversation}
          onCreateFolder={handleCreateFolder}
          onDeleteFolder={handleDeleteFolder}
          onUpdateFolder={handleUpdateFolder}
          onMoveConversation={handleMoveConversation}
          loading={loading}
        />
      }
    >
      <ChatWindow
        conversation={currentConversation}
        isLoading={loading && !streamingMsgId}
        streamingMsgId={streamingMsgId}
        streamingText={streamingText}
      />
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSendMessage}
        disabled={loading}
        loading={loading}
        detectedMetadata={detectedMetadata}
        pendingDocument={pendingDocument}
        onDocumentUploaded={(doc) => setPendingDocument(doc)}
        onClearDocument={() => setPendingDocument(null)}
      />
    </Layout>
  );
};

export default Home;
