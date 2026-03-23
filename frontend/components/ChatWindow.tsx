import React from 'react';
import { ConversationThread } from '@/types';
import { MessageItem } from './MessageItem';
import { ScrollArea } from './ScrollArea';

interface ChatWindowProps {
  conversation: ConversationThread | null;
  isLoading?: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ conversation, isLoading = false }) => {
  if (!conversation) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-white">
        <div className="text-center">
          <h1 className="mb-2 text-4xl font-bold text-gray-900">
            Academic Content Generator
          </h1>
          <p className="mb-8 text-gray-600">
            Generate exams, slideshows, guides, and more with AI
          </p>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">📝 Generate Exams</h3>
              <p className="text-sm text-gray-600">
                Create customized exams with multiple question types
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">🎬 Create Slideshows</h3>
              <p className="text-sm text-gray-600">
                Design engaging presentations on any topic
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">📚 Write Guides</h3>
              <p className="text-sm text-gray-600">
                Produce comprehensive study and teaching guides
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">✏️ Refine with Feedback</h3>
              <p className="text-sm text-gray-600">
                Iteratively improve content with human input
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <ScrollArea className="flex-1">
        <div className="pb-4">
          {conversation.messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center py-12">
              <p className="text-center text-gray-500">
                No messages yet. Start a conversation!
              </p>
            </div>
          ) : (
            conversation.messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))
          )}
          {isLoading && (
            <MessageItem
              message={{
                id: 'loading',
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
              }}
              isLoading={true}
            />
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
