/**
 * /documents - Document management page.
 * Lists all uploaded documents and allows uploading new ones for the RAG pipeline.
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { Sidebar } from '@/components/Sidebar';
import { DocumentUploader } from '@/components/DocumentUploader';
import { useAppStore } from '@/store/appStore';
import { useConversations } from '@/hooks/useApi';
import { apiClient } from '@/lib/api';
import { useT } from '@/hooks/useT';
import { tr } from '@/lib/translations';
import { Trash2, FileText, Eye } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';

const DocumentsPage: React.FC = () => {
  const router = useRouter();
  const T = useT();
  const {
    conversations,
    currentConversation,
    documents,
    setConversations,
    setCurrentConversation,
    setDocuments,
    addDocument,
  } = useAppStore();
  const { fetchConversations } = useConversations();
  const [isLoading, setIsLoading] = useState(false);
  const [showUploader, setShowUploader] = useState(false);
  const [subject, setSubject] = useState('');
  const [viewingChunks, setViewingChunks] = useState<{ docId: string; chunks: any[] } | null>(null);

  useEffect(() => {
    fetchConversations();
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.getConversations();
      // Documents come from the backend – use a dedicated endpoint when available
      // For now we list documents from the store
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploaded = (result: any) => {
    addDocument({
      id: result.id,
      userId: '',
      filename: result.filename || 'Uploaded file',
      fileType: result.file_type || 'txt',
      originalContent: '',
      source: 'pdf_upload',
      processed: true,
      subject: subject || 'Auto-detected',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
    setShowUploader(false);
    toast.success(`${T(tr.docs.processedPrefix)} ${result.chunks_count ?? 0} ${T(tr.docs.processed)}`);
  };

  const handleViewChunks = async (docId: string) => {
    try {
      const response = await apiClient.getDocumentChunks(docId);
      setViewingChunks({ docId, chunks: response.data.chunks });
    } catch {
      toast.error(T(tr.docs.chunkFetchErr));
    }
  };

  return (
    <Layout
      sidebar={
        <Sidebar
          conversations={conversations}
          currentConversationId={currentConversation?.id || null}
          onSelectConversation={(id) => {
            const conv = conversations.find((c) => c.id === id);
            setCurrentConversation(conv || null);
            router.push('/');
          }}
          onDeleteConversation={async (id) => {
            try {
              await apiClient.deleteConversation(id);
              setConversations(conversations.filter((c) => c.id !== id));
              if (currentConversation?.id === id) setCurrentConversation(null);
              toast.success(T(tr.docs.convDeleted));
            } catch {
              toast.error(T(tr.docs.convDeleteErr));
            }
          }}
          onNewConversation={() => router.push('/')}
        />
      }
    >
      <div className="flex h-full flex-col overflow-y-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{T(tr.docs.title)}</h1>
          <button
            onClick={() => setShowUploader(!showUploader)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            {T(tr.docs.upload)}
          </button>
        </div>

        {showUploader && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
            <h2 className="font-semibold text-gray-800">{T(tr.docs.uploadNew)}</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {T(tr.docs.subject)} <span className="text-gray-400 font-normal">{T(tr.docs.subjectHint)}</span>
              </label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder={T(tr.docs.subjectPlaceholder)}
                className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <DocumentUploader subject={subject || undefined} onUploaded={handleUploaded} />
          </div>
        )}

        {/* Chunks modal */}
        {viewingChunks && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-semibold text-gray-900">{T(tr.docs.chunksTitle)}</h2>
                <button onClick={() => setViewingChunks(null)} className="text-gray-400 hover:text-gray-600">✕</button>
              </div>
              <div className="space-y-3">
                {viewingChunks.chunks.map((chunk: any) => (
                  <div key={chunk.id} className="rounded-lg border border-gray-200 p-3 text-sm">
                    <p className="mb-1 text-xs text-gray-500">Chunk #{chunk.chunk_index} · {chunk.chunk_size} chars</p>
                    <p className="text-gray-700 whitespace-pre-wrap">{chunk.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Document list */}
        {documents.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-gray-400">
            {T(tr.docs.noDocuments)}
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4"
              >
                <FileText className="h-6 w-6 flex-shrink-0 text-indigo-500" />
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium text-gray-800">{doc.filename}</p>
                  <p className="text-xs text-gray-500">
                    {doc.subject || T(tr.docs.autoDetected)} · {formatDistanceToNow(new Date(doc.createdAt), { addSuffix: true })}
                  </p>
                </div>
                <button
                  onClick={() => handleViewChunks(doc.id)}
                  className="flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
                  title={T(tr.docs.chunksTitle)}
                >
                  <Eye className="h-3 w-3" /> {T(tr.docs.chunks)}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default DocumentsPage;
