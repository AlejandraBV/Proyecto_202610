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
import { Trash2, FileText, Eye } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';

const DocumentsPage: React.FC = () => {
  const router = useRouter();
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
  const [subject, setSubject] = useState('General');
  const [level, setLevel] = useState('university');
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
      id: result.documentId,
      userId: '',
      filename: result.filename || 'Uploaded file',
      fileType: result.fileType || 'txt',
      originalContent: '',
      source: 'pdf_upload',
      processed: true,
      subject,
      level,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
    setShowUploader(false);
    toast.success(`Document processed: ${result.chunksCount} chunks indexed`);
  };

  const handleViewChunks = async (docId: string) => {
    try {
      const response = await apiClient.getDocumentChunks(docId);
      setViewingChunks({ docId, chunks: response.data.chunks });
    } catch {
      toast.error('Failed to fetch document chunks');
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
              toast.success('Conversation deleted');
            } catch {
              toast.error('Failed to delete conversation');
            }
          }}
          onNewConversation={() => router.push('/')}
        />
      }
    >
      <div className="flex h-full flex-col overflow-y-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <button
            onClick={() => setShowUploader(!showUploader)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            + Upload Document
          </button>
        </div>

        {showUploader && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
            <h2 className="font-semibold text-gray-800">Upload a new document</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Level</label>
                <select
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="elementary">Elementary</option>
                  <option value="secondary">Secondary</option>
                  <option value="university">University</option>
                  <option value="professional">Professional</option>
                </select>
              </div>
            </div>
            <DocumentUploader subject={subject} level={level} onUploaded={handleUploaded} />
          </div>
        )}

        {/* Chunks modal */}
        {viewingChunks && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-semibold text-gray-900">Document Chunks</h2>
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
            No documents uploaded yet.
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
                    {doc.subject} · {doc.level} · {formatDistanceToNow(new Date(doc.createdAt), { addSuffix: true })}
                  </p>
                </div>
                <button
                  onClick={() => handleViewChunks(doc.id)}
                  className="flex items-center gap-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
                  title="View chunks"
                >
                  <Eye className="h-3 w-3" /> Chunks
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
