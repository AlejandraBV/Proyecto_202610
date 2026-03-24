import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';

/**
 * Hook for content generation and HITL regeneration.
 * Supports unlimited regeneration cycles (no retry cap).
 */
export function useContentGeneration() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const regenerate = useCallback(
    async (
      conversationId: string,
      contentId: string,
      feedbackText: string,
    ): Promise<any | null> => {
      setIsGenerating(true);
      setError(null);
      try {
        const response = await apiClient.regenerateContent(
          conversationId,
          contentId,
          feedbackText,
        );
        return response.data;
      } catch (err: any) {
        const msg =
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to regenerate content';
        setError(msg);
        return null;
      } finally {
        setIsGenerating(false);
      }
    },
    [],
  );

  return { regenerate, isGenerating, error };
}
