import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { ChatWindow } from '@/components/ChatWindow';
import { ChatInput } from '@/components/ChatInput';
import { useAppStore } from '@/store/appStore';
import { useConversations } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { ConversationThread, ContentType, DetectedMetadata } from '@/types';
import { v4 as uuidv4 } from 'uuid';
import toast from 'react-hot-toast';

const Dashboard: React.FC = () => {
  const router = useRouter();
  const [inputValue, setInputValue] = useState('');
  const [detectedMetadata, setDetectedMetadata] = useState<DetectedMetadata | null>(null);
  const {
    conversations,
    currentConversation,
    setConversations,
    setCurrentConversation,
    addMessage,
    addConversation,
    updateConversation,
    loading,
    setLoading,
  } = useAppStore();
  const { fetchConversations } = useConversations();

  useEffect(() => {
    fetchConversations();
  }, []);

  const handleNewConversation = () => {
    // With auto-topic detection, a new conversation is created automatically
    // when the user sends a message on a new topic. The user just needs to clear
    // the current conversation selection so the next message starts fresh.
    setCurrentConversation(null);
    setDetectedMetadata(null);
  };

  const handleSelectConversation = (id: string) => {
    const conv = conversations.find((c) => c.id === id);
    setCurrentConversation(conv || null);
    setDetectedMetadata(null);
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await apiClient.deleteConversation(id);
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);
      if (currentConversation?.id === id) {
        setCurrentConversation(null);
      }
      toast.success('Conversation deleted');
    } catch (error) {
      toast.error('Failed to delete conversation');
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const prompt = inputValue;
    setInputValue('');
    setLoading(true);

    // Add optimistic user message to the current conversation (if any)
    const tempUserMessage = {
      id: uuidv4(),
      role: 'user' as const,
      content: prompt,
      timestamp: new Date().toISOString(),
    };

    if (currentConversation) {
      addMessage(currentConversation.id, tempUserMessage);
    }

    try {
      const response = await apiClient.sendMessage({
        userPrompt: prompt,
        conversationId: currentConversation?.id ?? null,
      });

      const data = response.data;

      // Store auto-detected metadata for display
      setDetectedMetadata({
        subject: data.subject,
        topic: data.topic,
        contentType: data.contentType,
        confidence: data.confidence,
        detectionMethod: data.detectionMethod as any,
      });

      if (data.isNewConversation) {
        // The topic changed (or there was no conversation) – add the new one to the store
        const newConv: ConversationThread = {
          id: data.conversationId,
          title: data.title || `${data.subject || 'General'} - ${data.topic || 'Untitled'}`,
          subject: data.subject || 'General',
          topic: data.topic || 'Untitled',
          primarySubject: data.subject || undefined,
          primaryTopic: data.topic || undefined,
          userId: '',
          messages: [
            { ...tempUserMessage },
            {
              id: uuidv4(),
              role: 'assistant' as const,
              content: data.content,
              timestamp: new Date().toISOString(),
              contentType: (data.contentType as ContentType) || 'text',
            },
          ],
          generatedContent: [],
          documents: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        addConversation(newConv);
        setCurrentConversation(newConv);

        const label = data.subject && data.topic
          ? `${data.subject} – ${data.topic}`
          : 'new topic';
        toast.success(`Started new conversation: ${label}`, { duration: 3000 });
      } else {
        // Same topic – add the assistant reply to the existing conversation
        const assistantMessage = {
          id: uuidv4(),
          role: 'assistant' as const,
          content: data.content,
          timestamp: new Date().toISOString(),
          contentType: (data.contentType as any) || 'text',
        };
        addMessage(data.conversationId, assistantMessage);

        // Update conversation metadata if we have a better title now
        if (data.subject && data.topic) {
          updateConversation(data.conversationId, {
            subject: data.subject,
            topic: data.topic,
            primarySubject: data.subject,
            primaryTopic: data.topic,
          });
        }
      }
    } catch (error) {
      toast.error('Failed to send message');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout
      sidebar={
        <Sidebar
          conversations={conversations}
          currentConversationId={currentConversation?.id || null}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          onNewConversation={handleNewConversation}
          loading={loading}
        />
      }
    >
      <ChatWindow conversation={currentConversation} isLoading={loading} />
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSendMessage}
        disabled={loading}
        loading={loading}
        detectedMetadata={detectedMetadata}
      />
    </Layout>
  );
};

export default Dashboard;
