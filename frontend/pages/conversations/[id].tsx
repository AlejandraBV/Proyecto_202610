import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { ContentEditor } from '@/components/ContentEditor';
import { FeedbackPanel } from '@/components/FeedbackPanel';
import { ContentPreview } from '@/components/ContentPreview';
import { RegenerationButton } from '@/components/RegenerationButton';
import { useAppStore } from '@/store/appStore';
import { useConversations } from '@/hooks/useApi';
import { useFeedback } from '@/hooks/useFeedback';
import { useContentGeneration } from '@/hooks/useContentGeneration';
import { apiClient } from '@/lib/api';
import { GeneratedContent } from '@/types';
import toast from 'react-hot-toast';

const ConversationPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const {
    conversations,
    currentConversation,
    setConversations,
    setCurrentConversation,
  } = useAppStore();
  const { fetchConversations } = useConversations();
  const { submitFeedback, isSubmitting } = useFeedback();
  const { regenerate, isGenerating } = useContentGeneration();
  const [activeContent, setActiveContent] = useState<GeneratedContent | null>(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    if (id && conversations.length > 0) {
      const conv = conversations.find((c) => c.id === id);
      if (conv) {
        setCurrentConversation(conv);
        const last = conv.generatedContent[conv.generatedContent.length - 1];
        setActiveContent(last || null);
      }
    }
  }, [id, conversations]);

  const handleFeedback = async (
    contentId: string,
    feedback: string,
    status: 'approved' | 'needs_revision' | 'rejected',
    editorName?: string,
  ) => {
    const result = await submitFeedback(contentId, feedback, status, editorName);
    if (result) {
      toast.success('Feedback saved');
    } else {
      toast.error('Failed to save feedback');
    }
  };

  const handleRegenerate = async (contentId: string, feedback: string) => {
    if (!currentConversation) return;
    const result = await regenerate(currentConversation.id, contentId, feedback);
    if (result) {
      toast.success(`New version generated (v${result.version})`);
      // Refresh conversations to get updated content
      await fetchConversations();
    } else {
      toast.error('Regeneration failed');
    }
  };

  const handleSelectConversation = (cid: string) => {
    router.push(`/conversations/${cid}`);
  };

  const handleDeleteConversation = async (cid: string) => {
    try {
      await apiClient.deleteConversation(cid);
      setConversations(conversations.filter((c) => c.id !== cid));
      if (currentConversation?.id === cid) {
        router.push('/');
      }
      toast.success('Conversation deleted');
    } catch {
      toast.error('Failed to delete conversation');
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
          onNewConversation={() => router.push('/')}
        />
      }
    >
      <div className="flex h-full flex-col overflow-y-auto p-6 space-y-6">
        {currentConversation ? (
          <>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {currentConversation.title}
              </h1>
              <p className="text-sm text-gray-500">
                {currentConversation.primarySubject || currentConversation.subject} &bull;{' '}
                {currentConversation.primaryTopic || currentConversation.topic}
              </p>
            </div>

            {activeContent ? (
              <>
                <ContentEditor content={activeContent} readOnly />
                <FeedbackPanel
                  contentId={activeContent.id}
                  onSubmit={handleFeedback}
                  onRegenerate={handleRegenerate}
                  isSubmitting={isSubmitting}
                  isRegenerating={isGenerating}
                />
              </>
            ) : (
              <p className="text-gray-500">No generated content yet.</p>
            )}

            {/* Show all content versions */}
            {currentConversation.generatedContent.length > 1 && (
              <div className="space-y-4">
                <h2 className="font-semibold text-gray-700">Previous Versions</h2>
                {currentConversation.generatedContent
                  .slice(0, -1)
                  .reverse()
                  .map((gc) => (
                    <ContentPreview key={gc.id} content={gc} />
                  ))}
              </div>
            )}
          </>
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-gray-400">Select a conversation from the sidebar.</p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default ConversationPage;
