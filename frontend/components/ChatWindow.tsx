import React from 'react';
import { ConversationThread } from '@/types';
import { MessageItem } from './MessageItem';
import { ScrollArea } from './ScrollArea';
import { useT } from '@/hooks/useT';
import { tr } from '@/lib/translations';

interface ChatWindowProps {
  conversation: ConversationThread | null;
  isLoading?: boolean;
  streamingMsgId?: string | null;
  streamingText?: string;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  conversation,
  isLoading = false,
  streamingMsgId = null,
  streamingText = '',
}) => {
  const T = useT();

  if (!conversation) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-white">
        <div className="text-center">
          <h1 className="mb-2 text-4xl font-bold text-gray-900">
            {T(tr.chatWindow.title)}
          </h1>
          <p className="mb-8 text-gray-600">
            {T(tr.chatWindow.subtitle)}
          </p>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">{T(tr.chatWindow.card1Title)}</h3>
              <p className="text-sm text-gray-600">{T(tr.chatWindow.card1Body)}</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">{T(tr.chatWindow.card2Title)}</h3>
              <p className="text-sm text-gray-600">{T(tr.chatWindow.card2Body)}</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">{T(tr.chatWindow.card3Title)}</h3>
              <p className="text-sm text-gray-600">{T(tr.chatWindow.card3Body)}</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-4">
              <h3 className="mb-2 font-semibold text-gray-900">{T(tr.chatWindow.card4Title)}</h3>
              <p className="text-sm text-gray-600">{T(tr.chatWindow.card4Body)}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0 flex-col bg-white">
      <ScrollArea className="flex-1">
        <div className="pb-4">
          {conversation.messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center py-12">
              <p className="text-center text-gray-500">
                {T(tr.chatWindow.noMessages)}
              </p>
            </div>
          ) : (
            conversation.messages.map((message) => (
              <MessageItem
                key={message.id}
                message={
                  streamingMsgId && message.id === streamingMsgId
                    ? { ...message, content: streamingText }
                    : message
                }
                conversationId={conversation.id}
                isStreaming={streamingMsgId === message.id}
              />
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
