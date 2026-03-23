import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { ChatWindow } from '@/components/ChatWindow';
import { ChatInput } from '@/components/ChatInput';
import { useAppStore } from '@/store/appStore';
import { useConversations } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { v4 as uuidv4 } from 'uuid';
import toast from 'react-hot-toast';

const Dashboard: React.FC = () => {
  const router = useRouter();
  const [inputValue, setInputValue] = useState('');
  const {
    conversations,
    currentConversation,
    setConversations,
    setCurrentConversation,
    addMessage,
    loading,
    setLoading,
  } = useAppStore();
  const { fetchConversations, createConversation } = useConversations();

  useEffect(() => {
    fetchConversations();
  }, []);

  const handleNewConversation = async () => {
    try {
      const newConv = await createConversation({
        title: 'New Conversation',
        subject: 'General',
        topic: 'Untitled',
      });
      setCurrentConversation(newConv);
    } catch (error) {
      toast.error('Failed to create conversation');
    }
  };

  const handleSelectConversation = (id: string) => {
    const conv = conversations.find((c) => c.id === id);
    setCurrentConversation(conv || null);
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
    if (!inputValue.trim() || !currentConversation) return;

    const userMessage = {
      id: uuidv4(),
      role: 'user' as const,
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    addMessage(currentConversation.id, userMessage);
    setInputValue('');
    setLoading(true);

    try {
      // Use RAG-powered content generation
      const response = await apiClient.generateContentWithRAG(currentConversation.id, {
        prompt: inputValue,
        contentType: 'text', // Could be dynamic based on user input analysis
        subject: currentConversation.subject,
        topic: currentConversation.topic,
        level: 'university', // Could be dynamic
        retrievedContext: [], // Will be filled by backend RAG pipeline
        fewShotExamples: [], // Will be retrieved by backend
      });

      const assistantMessage = {
        id: uuidv4(),
        role: 'assistant' as const,
        content: response.data.content,
        timestamp: new Date().toISOString(),
        contentType: response.data.contentType,
        retrievedChunks: response.data.retrievedChunks,
        agentDecisions: response.data.agentDecisions,
      };

      addMessage(currentConversation.id, assistantMessage);

      // Show success message with RAG info
      const chunksUsed = response.data.retrievedChunks?.length || 0;
      const iterations = response.data.iterations || 1;
      toast.success(
        `Content generated using ${chunksUsed} source chunks (${iterations} iteration${iterations > 1 ? 's' : ''})`
      );
    } catch (error) {
      toast.error('Failed to generate content with RAG');
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
        disabled={!currentConversation || loading}
        loading={loading}
      />
    </Layout>
  );
};

export default Dashboard;
