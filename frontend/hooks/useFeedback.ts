import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';

type FeedbackStatus = 'approved' | 'needs_revision' | 'rejected';

/**
 * Hook for submitting teacher feedback and triggering regeneration.
 * The backend supports unlimited HITL cycles.
 */
export function useFeedback() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitFeedback = useCallback(
    async (
      contentId: string,
      feedback: string,
      status: FeedbackStatus,
      editorName?: string,
    ): Promise<{ feedbackId: string; nextAction: string } | null> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const response = await apiClient.submitContentFeedback(
          contentId,
          feedback,
          status,
          editorName,
        );
        return {
          feedbackId: response.data.feedback_id,
          nextAction: response.data.next_action,
        };
      } catch (err: any) {
        const msg =
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to submit feedback';
        setError(msg);
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return { submitFeedback, isSubmitting, error };
}
