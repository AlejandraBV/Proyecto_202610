import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';
import { DocumentUploadResponse } from '@/types';

/**
 * Hook for drag-and-drop document upload handling.
 */
export function useDocumentUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(
    async (
      file: File,
      subject: string,
      level: string,
      description?: string,
    ): Promise<DocumentUploadResponse | null> => {
      setIsUploading(true);
      setProgress(0);
      setError(null);

      try {
        const response = await apiClient.uploadDocument(file, {
          subject,
          level,
          description,
        });
        setProgress(100);
        return response.data;
      } catch (err: any) {
        const msg =
          err?.response?.data?.detail ||
          err?.message ||
          'Upload failed';
        setError(msg);
        return null;
      } finally {
        setIsUploading(false);
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setProgress(0);
    setError(null);
  }, []);

  return { upload, isUploading, progress, error, reset };
}
