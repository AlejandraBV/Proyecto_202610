/**
 * /dashboard - Teacher dashboard overview page.
 * Re-uses the main chat interface from the index page and adds a quick-stats
 * bar at the top so teachers can see their activity at a glance.
 */
import React, { useEffect } from 'react';
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
import { BookOpen, FileText, MessageSquare } from 'lucide-react';

const Dashboard: React.FC = () => {
  const router = useRouter();
  const [inputValue, setInputValue] = React.useState('');
  const [detectedMetadata, setDetectedMetadata] = React.useState<DetectedMetadata | null>(null);
  const {
    conversations,
    currentConversation,
    setConversations,
    setCurrentConversation,
    addMessage,
    addConversation,
    updateConversation,
    documents,
    loading,
    setLoading,
  } = useAppStore();
  const { fetchConversations } = useConversations();

  useEffect(() => {
    fetchConversations();
  }, []);

  const totalContent = conversations.reduce(
    (sum, c) => sum + c.generatedContent.length,
    0,
  );

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const prompt = inputValue;
    setInputValue('');
    setLoading(true);

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

      setDetectedMetadata({
        subject: data.subject,
        topic: data.topic,
        contentType: data.contentType,
        confidence: data.confidence,
        detectionMethod: data.detectionMethod as any,
      });

      if (data.isNewConversation) {
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
        const label = data.subject && data.topic ? `${data.subject} – ${data.topic}` : 'new topic';
        toast.success(`Started new conversation: ${label}`, { duration: 3000 });
      } else {
        addMessage(data.conversationId, {
          id: uuidv4(),
          role: 'assistant' as const,
          content: data.content,
          timestamp: new Date().toISOString(),
          contentType: (data.contentType as any) || 'text',
        });
        if (data.subject && data.topic) {
          updateConversation(data.conversationId, {
            subject: data.subject,
            topic: data.topic,
            primarySubject: data.subject,
            primaryTopic: data.topic,
          });
        }
      }
    } catch {
      toast.error('Failed to send message');
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
          onSelectConversation={(id) => {
            const conv = conversations.find((c) => c.id === id);
            setCurrentConversation(conv || null);
          }}
          onDeleteConversation={async (id) => {
            try {
              await apiClient.deleteConversation(id);
              setConversations(conversations.filter((c) => c.id !== id));
              if (currentConversation?.id === id) setCurrentConversation(null);
              toast.success('Conversation deleted');
            } catch {
              toast.error('Failed to delete conversation');
            }
          }}
          onNewConversation={() => {
            setCurrentConversation(null);
            setDetectedMetadata(null);
          }}
          loading={loading}
        />
      }
    >
      {/* Stats bar */}
      <div className="flex gap-4 border-b border-gray-200 bg-gray-50 px-6 py-3 text-sm">
        <div className="flex items-center gap-2 text-gray-600">
          <MessageSquare className="h-4 w-4" />
          <span>{conversations.length} conversation{conversations.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-600">
          <FileText className="h-4 w-4" />
          <span>{totalContent} content item{totalContent !== 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-2 text-gray-600">
          <BookOpen className="h-4 w-4" />
          <span>{documents.length} document{documents.length !== 1 ? 's' : ''}</span>
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
      />
    </Layout>
  );
};

export default Dashboard;
