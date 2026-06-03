import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, ChunkResponse, AgentDecisionResponse, BloomTag } from '@/types';
import { Copy, Loader, ChevronDown, ChevronUp, FileText, Brain, CheckCircle, XCircle, AlertTriangle, Paperclip, Download, BookmarkPlus } from 'lucide-react';
import { useT } from '@/hooks/useT';
import { tr } from '@/lib/translations';
import toast from 'react-hot-toast';
import { MessageFeedback } from '@/components/MessageFeedback';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/store/appStore';

interface MessageItemProps {
  message: Message;
  isLoading?: boolean;
  isStreaming?: boolean;
  /** Required to submit ratings — pass the parent conversation ID. */
  conversationId?: string;
}

const RetrievedChunks: React.FC<{ chunks: ChunkResponse[] }> = ({ chunks }) => {
  const T = useT();
  const [isExpanded, setIsExpanded] = useState(false);

  if (!chunks || chunks.length === 0) return null;

  const label = chunks.length === 1 ? T(tr.message.sourceChunk) : T(tr.message.sourceChunks);

  return (
    <div className="mt-3 border-t border-gray-200 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-800 mb-2"
      >
        <FileText className="h-3 w-3" />
        {T(tr.message.retrieved)} {chunks.length} {label}
        {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {isExpanded && (
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {chunks.map((chunk, index) => (
            <div key={index} className="bg-blue-50 border border-blue-200 rounded p-2 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-blue-800">
                  {T(tr.message.chunk)} {chunk.chunkIndex + 1}
                  {chunk.sourceFile && ` ${T(tr.message.from)} ${chunk.sourceFile}`}
                </span>
                {chunk.similarityScore && (
                  <span className="text-blue-600">
                    {T(tr.message.similarity)} {(chunk.similarityScore * 100).toFixed(1)}%
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
  const T = useT();
  const [isExpanded, setIsExpanded] = useState(false);

  if (!decisions || decisions.length === 0) return null;

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'approved':       return <CheckCircle className="h-3 w-3 text-green-500" />;
      case 'needs_revision': return <AlertTriangle className="h-3 w-3 text-yellow-500" />;
      case 'regenerate':     return <XCircle className="h-3 w-3 text-red-500" />;
      default:               return <Brain className="h-3 w-3 text-gray-500" />;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'approved':       return 'text-green-700 bg-green-50 border-green-200';
      case 'needs_revision': return 'text-yellow-700 bg-yellow-50 border-yellow-200';
      case 'regenerate':     return 'text-red-700 bg-red-50 border-red-200';
      default:               return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="mt-3 border-t border-gray-200 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-gray-600 hover:text-gray-800 mb-2"
      >
        <Brain className="h-3 w-3" />
        {T(tr.message.agentDecisions)} ({decisions.length})
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
                    {T(tr.message.showMetadata)}
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

// ── Bloom's Taxonomy badge strip ─────────────────────────────────────────────

const BLOOM_COLORS: Record<string, string> = {
  green:  'bg-green-100 text-green-700 border-green-200',
  blue:   'bg-blue-100 text-blue-700 border-blue-200',
  yellow: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  orange: 'bg-orange-100 text-orange-700 border-orange-200',
  red:    'bg-red-100 text-red-700 border-red-200',
  purple: 'bg-purple-100 text-purple-700 border-purple-200',
};

const BloomBadges: React.FC<{ tags: BloomTag[] }> = ({ tags }) => {
  if (!tags || tags.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1 items-center">
      <span className="text-xs text-gray-400 mr-1">Bloom:</span>
      {tags.map((t) => (
        <span
          key={t.level}
          className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${BLOOM_COLORS[t.color] || 'bg-gray-100 text-gray-600 border-gray-200'}`}
          title={`${t.level}: ${t.count} item${t.count !== 1 ? 's' : ''}`}
        >
          {t.level}
          <span className="opacity-60">×{t.count}</span>
        </span>
      ))}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  isLoading = false,
  isStreaming = false,
  conversationId,
}) => {
  const T = useT();
  const [exporting, setExporting] = useState(false);
  const [savingToBank, setSavingToBank] = useState(false);

  // Resolve document filename: prefer explicit documentName on the message,
  // then look up from the documents store by documentId, then fall back to label.
  const documents = useAppStore((s) => s.documents);
  const resolvedDocName = message.documentName
    ?? (message.documentId ? documents.find((d) => d.id === message.documentId)?.filename : undefined)
    ?? (message.documentId ? T(tr.message.docAttached) : undefined);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    toast.success(T(tr.message.copied));
  };

  const handleExport = async (format: 'pdf' | 'docx') => {
    if (!conversationId) return;
    setExporting(true);
    try {
      await apiClient.exportMessage(conversationId, message.id, format);
      toast.success(`Downloaded as ${format.toUpperCase()}`);
    } catch {
      toast.error('Export failed. Try again.');
    } finally {
      setExporting(false);
    }
  };

  const handleSaveToBank = async () => {
    if (!conversationId) return;
    setSavingToBank(true);
    try {
      const saved = await apiClient.extractQuestionsFromMessage(message.id);
      const data = (saved as any).data as any[];
      toast.success(`${data.length} question${data.length !== 1 ? 's' : ''} saved to Question Bank`);
    } catch {
      toast.error('No numbered questions found. Use the Question Bank page to save manually.');
    } finally {
      setSavingToBank(false);
    }
  };

  return (
    <div
      className={`flex gap-3 py-4 px-4 ${
        message.role === 'user' ? 'bg-white' : 'bg-gray-50'
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
          {message.role === 'user' ? T(tr.message.you) : T(tr.message.assistant)}
        </div>

        {/* Document attachment chip */}
        {message.role === 'user' && message.documentId && resolvedDocName && (
          <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs text-blue-700" title={resolvedDocName}>
            <Paperclip className="h-3 w-3 flex-shrink-0" />
            <span className="truncate max-w-[220px] font-medium">{resolvedDocName}</span>
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-500">
            <Loader className="h-4 w-4 animate-spin" />
            <span>{T(tr.message.generating)}</span>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown
              components={{
                p:  ({ node, ...props }) => <p className="mb-2" {...props} />,
                ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-2" {...props} />,
                ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-2" {...props} />,
                li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                code: ({ node, ...props }) => {
                  const isInline = !String(props.children).includes('\n');
                  return isInline ? (
                    <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm" {...props} />
                  ) : (
                    <code className="block bg-gray-900 text-gray-100 p-3 rounded mb-2 overflow-x-auto" {...props} />
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-2 h-4 bg-gray-500 ml-0.5 animate-pulse align-middle" />
            )}
          </div>
        )}

        {message.role === 'assistant' && !isLoading && (
          <>
            <RetrievedChunks chunks={message.retrievedChunks || []} />
            <AgentDecisions decisions={message.agentDecisions || []} />
          </>
        )}

        {/* Bloom taxonomy badges (assistant messages only) */}
        {message.role === 'assistant' && !isLoading && message.bloomTags && message.bloomTags.length > 0 && (
          <BloomBadges tags={message.bloomTags} />
        )}

        {!isLoading && (
          <div className="mt-2 flex flex-wrap items-center gap-3">
            {/* Copy */}
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
            >
              <Copy className="h-3 w-3" />
              {T(tr.message.copy)}
            </button>

            {/* Export (assistant messages only) */}
            {message.role === 'assistant' && conversationId && (
              <>
                <button
                  onClick={() => handleExport('pdf')}
                  disabled={exporting}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 disabled:opacity-50"
                  title="Download as PDF"
                >
                  <Download className="h-3 w-3" />
                  PDF
                </button>
                <button
                  onClick={() => handleExport('docx')}
                  disabled={exporting}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 disabled:opacity-50"
                  title="Download as Word"
                >
                  <Download className="h-3 w-3" />
                  Word
                </button>
                <button
                  onClick={handleSaveToBank}
                  disabled={savingToBank}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-emerald-600 disabled:opacity-50"
                  title="Extract questions to Question Bank"
                >
                  <BookmarkPlus className="h-3 w-3" />
                  Save to Bank
                </button>
              </>
            )}
          </div>
        )}

        {/* Feedback / edit-and-refine — assistant messages only, once loaded */}
        {message.role === 'assistant' && !isLoading && conversationId && (
          <MessageFeedback
            messageId={message.id}
            conversationId={conversationId}
            originalContent={message.content}
          />
        )}
      </div>
    </div>
  );
};
