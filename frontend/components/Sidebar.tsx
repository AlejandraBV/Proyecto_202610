import React from 'react';
import Link from 'next/link';
import { ConversationThread } from '@/types';
import { Trash2, MessageCircle, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface SidebarProps {
  conversations: ConversationThread[];
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onNewConversation: () => void;
  loading?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewConversation,
  loading = false,
}) => {
  return (
    <div className="flex h-screen w-64 flex-col border-r border-gray-200 bg-white">
      {/* New Conversation Button */}
      <div className="border-b border-gray-200 p-4">
        <button
          onClick={onNewConversation}
          disabled={loading}
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:bg-gray-100 transition-colors"
        >
          + New Conversation
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            No conversations yet. Create one to get started!
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group rounded-lg p-3 cursor-pointer transition-colors ${
                  currentConversationId === conv.id
                    ? 'bg-gray-100'
                    : 'hover:bg-gray-50'
                }`}
              >
                <button
                  onClick={() => onSelectConversation(conv.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-start gap-2">
                    <MessageCircle className="h-4 w-4 mt-1 flex-shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-sm text-gray-800">
                        {conv.title}
                      </p>
                      <p className="truncate text-xs text-gray-500">
                        {conv.topic}
                      </p>
                      <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
                        <Clock className="h-3 w-3" />
                        {formatDistanceToNow(new Date(conv.updatedAt), { addSuffix: true })}
                      </div>
                    </div>
                  </div>
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  className="mt-2 hidden group-hover:flex w-full items-center justify-center gap-2 rounded px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="h-3 w-3" />
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User Info */}
      <div className="border-t border-gray-200 p-4 text-xs text-gray-500 text-center">
        <p>Academic Content Generator</p>
        <p>Powered by Gemini 1.5 Pro</p>
      </div>
    </div>
  );
};
