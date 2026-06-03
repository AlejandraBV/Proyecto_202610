/**
 * MessageFeedback
 * ───────────────
 * Two-action bar shown below every AI assistant message:
 *
 *   👍  Helpful — records a positive rating (silent, shows brief toast)
 *   ✏️  Edit    — expands an inline editor pre-filled with the message content.
 *                 When submitted, the original + edited text are sent to the LLM
 *                 which produces a polished refined version. That version is
 *                 appended to the conversation as a new assistant message.
 *
 * The main chat input is NEVER blocked — the editor is a collapsible panel
 * below the message and the user can cancel / keep chatting at any time.
 */
import React, { useState } from 'react';
import { ThumbsUp, Pencil, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import { useT } from '@/hooks/useT';
import { tr } from '@/lib/translations';
import toast from 'react-hot-toast';
import { Message } from '@/types';

interface MessageFeedbackProps {
  messageId: string;
  conversationId: string;
  /** Original content of the message — pre-fills the editor. */
  originalContent: string;
}

export const MessageFeedback: React.FC<MessageFeedbackProps> = ({
  messageId,
  conversationId,
  originalContent,
}) => {
  const T = useT();
  const addMessage = useAppStore((s) => s.addMessage);

  const [liked, setLiked] = useState(false);
  const [showEditor, setShowEditor] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [refining, setRefining] = useState(false);

  // ── 👍 Helpful rating ──────────────────────────────────────────────────
  const handleLike = async () => {
    if (liked) return;
    try {
      await apiClient.rateMessage(conversationId, messageId, 1);
      setLiked(true);
      toast.success(T(tr.feedback.thanks), { duration: 1500 });
    } catch {
      toast.error(T(tr.feedback.ratingError));
    }
  };

  // ── ✏️ Open editor ─────────────────────────────────────────────────────
  const handleOpenEditor = () => {
    setEditedContent(originalContent);
    setShowEditor(true);
  };

  const handleCancel = () => {
    setShowEditor(false);
    setEditedContent('');
  };

  // ── Submit edit → AI refinement ────────────────────────────────────────
  const handleRefine = async () => {
    const trimmed = editedContent.trim();
    if (!trimmed || trimmed === originalContent.trim()) {
      toast.error('No changes detected.');
      return;
    }

    setRefining(true);
    try {
      const response = await apiClient.refineMessage(conversationId, messageId, trimmed);
      const data = response.data as any;

      // Append the refined response to the conversation in the store
      const refinedMessage: Message = {
        id: data.message_id,
        role: 'assistant',
        content: data.content,
        timestamp: data.timestamp,
        contentType: data.content_type ?? undefined,
      };
      addMessage(conversationId, refinedMessage);

      toast.success(T(tr.feedback.refinedLabel));
      setShowEditor(false);
      setEditedContent('');
    } catch {
      toast.error(T(tr.feedback.refineError));
    } finally {
      setRefining(false);
    }
  };

  return (
    <div className="mt-2 space-y-2">
      {/* Action buttons row — always visible */}
      <div className="flex items-center gap-1.5">
        {/* 👍 Helpful */}
        <button
          onClick={handleLike}
          title={T(tr.feedback.helpful)}
          className={`flex items-center gap-1 rounded-md px-1.5 py-1 text-xs transition-colors ${
            liked
              ? 'bg-green-100 text-green-700'
              : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
          }`}
        >
          <ThumbsUp className="h-3.5 w-3.5" />
          {liked && <span className="text-green-600">{T(tr.feedback.thanks)}</span>}
        </button>

        {/* ✏️ Edit output */}
        <button
          onClick={showEditor ? handleCancel : handleOpenEditor}
          title={T(tr.feedback.editOutput)}
          className={`flex items-center gap-1 rounded-md px-1.5 py-1 text-xs transition-colors ${
            showEditor
              ? 'bg-indigo-100 text-indigo-700'
              : 'text-gray-400 hover:text-indigo-600 hover:bg-indigo-50'
          }`}
        >
          <Pencil className="h-3.5 w-3.5" />
          <span>{T(tr.feedback.editOutput)}</span>
        </button>
      </div>

      {/* ── Inline editor panel ─────────────────────────────────────────── */}
      {showEditor && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-3 space-y-2.5">
          <p className="text-xs text-indigo-700 font-medium">{T(tr.feedback.editHint)}</p>

          <textarea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            disabled={refining}
            rows={Math.min(Math.max(editedContent.split('\n').length + 2, 6), 20)}
            className={`w-full rounded-lg border px-3 py-2 text-sm font-mono leading-relaxed resize-y
              focus:outline-none focus:ring-2 focus:ring-indigo-400
              ${refining
                ? 'border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'border-indigo-300 bg-white text-gray-800'
              }`}
          />

          <div className="flex items-center gap-2">
            <button
              disabled={refining || !editedContent.trim()}
              onClick={handleRefine}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white
                hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {refining
                ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> {T(tr.feedback.refining)}</>
                : T(tr.feedback.refineWithAI)
              }
            </button>

            <button
              disabled={refining}
              onClick={handleCancel}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-600
                hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {T(tr.feedback.cancel)}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
