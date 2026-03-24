import React, { useState } from 'react';
import { RegenerationButton } from './RegenerationButton';

type FeedbackStatus = 'approved' | 'needs_revision' | 'rejected';

interface FeedbackPanelProps {
  contentId: string;
  onSubmit: (
    contentId: string,
    feedback: string,
    status: FeedbackStatus,
    editorName?: string,
  ) => Promise<any>;
  onRegenerate?: (contentId: string, feedback: string) => Promise<void>;
  isSubmitting?: boolean;
  isRegenerating?: boolean;
}

/**
 * Panel for submitting teacher feedback with optional regeneration trigger.
 * Supports unlimited HITL cycles – no retry cap enforced on the frontend.
 */
export const FeedbackPanel: React.FC<FeedbackPanelProps> = ({
  contentId,
  onSubmit,
  onRegenerate,
  isSubmitting = false,
  isRegenerating = false,
}) => {
  const [feedback, setFeedback] = useState('');
  const [status, setStatus] = useState<FeedbackStatus>('needs_revision');
  const [editorName, setEditorName] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;
    await onSubmit(contentId, feedback, status, editorName || undefined);
    setSubmitted(true);
  };

  const handleRegenerate = async () => {
    if (!onRegenerate || !feedback.trim()) return;
    await onRegenerate(contentId, feedback);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-3"
    >
      <h3 className="font-medium text-gray-800">Provide Feedback</h3>

      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Describe what you'd like to improve…"
        rows={4}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />

      <div className="flex flex-wrap gap-3">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as FeedbackStatus)}
          className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="approved">✅ Approved</option>
          <option value="needs_revision">🔄 Needs Revision</option>
          <option value="rejected">❌ Rejected</option>
        </select>

        <input
          value={editorName}
          onChange={(e) => setEditorName(e.target.value)}
          placeholder="Your name (optional)"
          className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isSubmitting || !feedback.trim()}
          className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
        >
          {isSubmitting ? 'Saving…' : 'Save Feedback'}
        </button>

        {onRegenerate && (
          <RegenerationButton
            onClick={handleRegenerate}
            loading={isRegenerating}
            disabled={!feedback.trim()}
          />
        )}

        {submitted && (
          <span className="text-sm text-green-600">Feedback saved ✓</span>
        )}
      </div>
    </form>
  );
};
