import React, { useState, useRef } from 'react';
import { MessageCircle, Send, Plus, Loader, Upload, Link, FileText } from 'lucide-react';
import { useDocuments } from '@/hooks/useApi';
import { useAppStore } from '@/store/appStore';
import { DocumentUploadRequest, DetectedMetadata } from '@/types';
import toast from 'react-hot-toast';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onFileUpload?: (file: File) => void;
  disabled?: boolean;
  loading?: boolean;
  /** Auto-detected topic metadata returned by the backend after the last send */
  detectedMetadata?: DetectedMetadata | null;
}

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, request: DocumentUploadRequest) => Promise<void>;
  onUrlUpload: (url: string, request: DocumentUploadRequest) => Promise<void>;
}

const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose, onUpload, onUrlUpload }) => {
  const [uploadType, setUploadType] = useState<'file' | 'url'>('file');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [subject, setSubject] = useState('');
  const [level, setLevel] = useState('');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject || !level) {
      toast.error('Subject and level are required');
      return;
    }

    const request: DocumentUploadRequest = { subject, level, description };

    try {
      setUploading(true);
      if (uploadType === 'file' && file) {
        await onUpload(file, request);
        toast.success('Document uploaded successfully!');
      } else if (uploadType === 'url' && url) {
        await onUrlUpload(url, request);
        toast.success('Document fetched from URL successfully!');
      }
      onClose();
      // Reset form
      setFile(null);
      setUrl('');
      setSubject('');
      setLevel('');
      setDescription('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (error) {
      // Error already handled in hook
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold mb-4">Upload Document</h3>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setUploadType('file')}
            className={`flex-1 py-2 px-3 rounded ${uploadType === 'file' ? 'bg-primary text-white' : 'bg-gray-100'}`}
          >
            <FileText className="inline w-4 h-4 mr-1" />
            File
          </button>
          <button
            onClick={() => setUploadType('url')}
            className={`flex-1 py-2 px-3 rounded ${uploadType === 'url' ? 'bg-primary text-white' : 'bg-gray-100'}`}
          >
            <Link className="inline w-4 h-4 mr-1" />
            URL
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {uploadType === 'file' ? (
            <div>
              <label className="block text-sm font-medium mb-1">Select File</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full p-2 border border-gray-300 rounded"
                required
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium mb-1">URL</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/document.pdf"
                className="w-full p-2 border border-gray-300 rounded"
                required
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium mb-1">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Mathematics"
                className="w-full p-2 border border-gray-300 rounded"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Level</label>
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded"
                required
              >
                <option value="">Select level</option>
                <option value="elementary">Elementary</option>
                <option value="secondary">Secondary</option>
                <option value="university">University</option>
                <option value="professional">Professional</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description (Optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the document"
              className="w-full p-2 border border-gray-300 rounded"
              rows={2}
            />
          </div>

          <div className="flex gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading || (uploadType === 'file' && !file) || (uploadType === 'url' && !url)}
              className="flex-1 py-2 px-4 bg-primary text-white rounded hover:bg-primary/90 disabled:bg-gray-300"
            >
              {uploading ? <Loader className="inline w-4 h-4 animate-spin mr-1" /> : <Upload className="inline w-4 h-4 mr-1" />}
              Upload
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSubmit,
  onFileUpload,
  disabled = false,
  loading = false,
  detectedMetadata,
}) => {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const { uploadDocument, uploadFromUrl } = useDocuments();

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      onSubmit();
    }
  };

  const handleFileUpload = async (file: File, request: DocumentUploadRequest) => {
    await uploadDocument(file, request);
  };

  const handleUrlUpload = async (url: string, request: DocumentUploadRequest) => {
    await uploadFromUrl(url, request);
  };

  return (
    <>
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="mx-auto max-w-4xl">
          <div className="flex gap-2">
            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center justify-center rounded-lg p-2 hover:bg-gray-100 transition-colors"
              title="Upload document for RAG"
            >
              <Plus className="h-5 w-5 text-gray-500" />
            </button>

            <div className="flex-1 flex gap-2">
              <div className="flex-1 relative">
                <textarea
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask me to generate exams, slideshows, guides... (Ctrl+Enter to send)"
                  disabled={disabled || loading}
                  rows={3}
                  className="w-full resize-none rounded-lg border border-gray-300 bg-white p-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:bg-gray-50 disabled:text-gray-500"
                />
              </div>

              <button
                onClick={onSubmit}
                disabled={disabled || loading || !value.trim()}
                className="flex items-center justify-center rounded-lg bg-primary px-4 py-3 text-white hover:bg-primary/90 disabled:bg-gray-300 transition-colors"
                aria-label="Send message"
              >
                {loading ? (
                  <Loader className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          <p className="mt-2 text-center text-xs text-gray-500">
            Upload documents for enhanced RAG-powered content generation. Your data is private and secure.
          </p>

          {/* Auto-detected metadata badge */}
          {detectedMetadata && (detectedMetadata.subject || detectedMetadata.topic) && (
            <div className="mt-2 flex items-center justify-center gap-1 text-xs text-primary">
              <span>📚</span>
              {detectedMetadata.subject && <span>{detectedMetadata.subject}</span>}
              {detectedMetadata.subject && detectedMetadata.topic && <span>•</span>}
              {detectedMetadata.topic && <span>{detectedMetadata.topic}</span>}
              {detectedMetadata.contentType && (
                <>
                  <span>•</span>
                  <span className="capitalize">{detectedMetadata.contentType}</span>
                </>
              )}
              {detectedMetadata.detectionMethod && (
                <span className="ml-1 text-gray-400">
                  (via {detectedMetadata.detectionMethod})
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <UploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUpload={handleFileUpload}
        onUrlUpload={handleUrlUpload}
      />
    </>
  );
};
