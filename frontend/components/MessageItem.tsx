import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, ChunkResponse, AgentDecisionResponse } from '@/types';
import { Copy, Loader, ChevronDown, ChevronUp, FileText, Brain, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

interface MessageItemProps {
  message: Message;
  isLoading?: boolean;
}

const RetrievedChunks: React.FC<{ chunks: ChunkResponse[] }> = ({ chunks }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!chunks || chunks.length === 0) return null;

  return (
    <div className="mt-3 border-t border-gray-200 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-800 mb-2"
      >
        <FileText className="h-3 w-3" />
        Retrieved {chunks.length} source chunk{chunks.length !== 1 ? 's' : ''}
        {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {isExpanded && (
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {chunks.map((chunk, index) => (
            <div key={index} className="bg-blue-50 border border-blue-200 rounded p-2 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-blue-800">
                  Chunk {chunk.chunkIndex + 1}
                  {chunk.sourceFile && ` from ${chunk.sourceFile}`}
                </span>
                {chunk.similarityScore && (
                  <span className="text-blue-600">
                    Similarity: {(chunk.similarityScore * 100).toFixed(1)}%
                  </span>
                )}
              </div>
              <p className="text-blue-900 line-clamp-3">{chunk.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const AgentDecisions: React.FC<{ decisions: AgentDecisionResponse[] }> = ({ decisions }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!decisions || decisions.length === 0) return null;

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'approved': return <CheckCircle className="h-3 w-3 text-green-500" />;
      case 'needs_revision': return <AlertTriangle className="h-3 w-3 text-yellow-500" />;
      case 'regenerate': return <XCircle className="h-3 w-3 text-red-500" />;
      default: return <Brain className="h-3 w-3 text-gray-500" />;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'approved': return 'text-green-700 bg-green-50 border-green-200';
      case 'needs_revision': return 'text-yellow-700 bg-yellow-50 border-yellow-200';
      case 'regenerate': return 'text-red-700 bg-red-50 border-red-200';
      default: return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="mt-3 border-t border-gray-200 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-800 mb-2"
      >
        <Brain className="h-3 w-3" />
        Agent Decisions ({decisions.length})
        {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {isExpanded && (
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {decisions.map((decision, index) => (
            <div key={index} className={`border rounded p-2 text-xs ${getDecisionColor(decision.decision)}`}>
              <div className="flex items-center gap-2 mb-1">
                {getDecisionIcon(decision.decision)}
                <span className="font-medium capitalize">{decision.agentName} Agent</span>
                <span className="text-gray-500">•</span>
                <span className="capitalize">{decision.decision.replace('_', ' ')}</span>
              </div>
              <p className="text-gray-800">{decision.reasoning}</p>
              {decision.metadata && Object.keys(decision.metadata).length > 0 && (
                <details className="mt-1">
                  <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                    Show metadata
                  </summary>
                  <pre className="mt-1 text-xs bg-white p-1 rounded border overflow-x-auto">
                    {JSON.stringify(decision.metadata, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const MessageItem: React.FC<MessageItemProps> = ({ message, isLoading = false }) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    toast.success('Copied to clipboard');
  };

  return (
    <div
      className={`flex gap-3 py-4 px-4 ${
        message.role === 'user'
          ? 'bg-white'
          : 'bg-gray-50'
      }`}
    >
      <div className="flex-shrink-0">
        <div
          className={`flex h-8 w-8 items-center justify-center rounded-full font-semibold text-white ${
            message.role === 'user' ? 'bg-blue-500' : 'bg-primary'
          }`}
        >
          {message.role === 'user' ? 'U' : 'A'}
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="mb-1 text-xs font-semibold text-gray-600">
          {message.role === 'user' ? 'You' : 'Academic Generator'}
        </div>

        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-500">
            <Loader className="h-4 w-4 animate-spin" />
            <span>Generating response with RAG...</span>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown
              components={{
                p: ({ node, ...props }) => <p className="mb-2" {...props} />,
                ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-2" {...props} />,
                ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-2" {...props} />,
                li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                code: ({ node, inline, ...props }) =>
                  inline ? (
                    <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm" {...props} />
                  ) : (
                    <code className="block bg-gray-900 text-gray-100 p-3 rounded mb-2 overflow-x-auto" {...props} />
                  ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* RAG Information */}
        {message.role === 'assistant' && !isLoading && (
          <>
            <RetrievedChunks chunks={message.retrievedChunks || []} />
            <AgentDecisions decisions={message.agentDecisions || []} />
          </>
        )}

        {!isLoading && (
          <button
            onClick={handleCopy}
            className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
          >
            <Copy className="h-3 w-3" />
            Copy
          </button>
        )}
      </div>
    </div>
  );
};
