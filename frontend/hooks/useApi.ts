import { useCallback } from 'react';
import { apiClient, ApiError } from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import { DocumentUploadRequest, SemanticSearchRequest } from '@/types';

export const useApi = () => {
  const { setLoading, setError } = useAppStore();

  const handleError = useCallback((error: ApiError) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    setError(message);
    console.error('API Error:', message);
  }, [setError]);

  return { apiClient, handleError, setLoading, setError };
};

export const useConversations = () => {
  const { setLoading, setError } = useAppStore();
  const { setConversations, addConversation, updateConversation } = useAppStore();

  const fetchConversations = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.getConversations();
      setConversations(response.data);
    } catch (error) {
      setError('Failed to fetch conversations');
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setConversations]);

  const createConversation = useCallback(async (data: any) => {
    try {
      setLoading(true);
      const response = await apiClient.createConversation(data);
      addConversation(response.data);
      return response.data;
    } catch (error) {
      setError('Failed to create conversation');
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, addConversation]);

  return { fetchConversations, createConversation };
};

export const useDocuments = () => {
  const { setLoading, setError } = useAppStore();
  const { addDocument, setRetrievedChunks } = useAppStore();

  const uploadDocument = useCallback(async (file: File, request: DocumentUploadRequest) => {
    try {
      setLoading(true);
      const response = await apiClient.uploadDocument(file, request);
      addDocument(response.data as any); // Document will be added to conversation
      return response.data;
    } catch (error) {
      setError('Failed to upload document');
      throw error;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, addDocument]);

  const uploadFromUrl = useCallback(async (url: string, request: DocumentUploadRequest) => {
    try {
      setLoading(true);
      const response = await apiClient.uploadFromUrl(url, request);
      addDocument(response.data as any);
      return response.data;
    } catch (error) {
      setError('Failed to fetch from URL');
      throw error;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, addDocument]);

  const semanticSearch = useCallback(async (request: SemanticSearchRequest) => {
    try {
      setLoading(true);
      const response = await apiClient.semanticSearch(request);
      setRetrievedChunks(response.data.chunks);
      return response.data;
    } catch (error) {
      setError('Failed to search documents');
      throw error;
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setRetrievedChunks]);

  return { uploadDocument, uploadFromUrl, semanticSearch };
};
