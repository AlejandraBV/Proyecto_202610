import React, { useCallback, useState } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import { useDocumentUpload } from '@/hooks/useDocumentUpload';

interface DocumentUploaderProps {
  subject?: string;
  onUploaded?: (result: any) => void;
}

/**
 * Drag-and-drop document uploader component.
 * Supports PDF, DOCX, and TXT files.
 */
export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  subject,
  onUploaded,
}) => {
  const { upload, isUploading, progress, error, reset } = useDocumentUpload();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setSelectedFile(file);
      const result = await upload(file, subject);
      if (result && onUploaded) {
        onUploaded(result);
      }
    },
    [upload, subject, onUploaded],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const clearFile = () => {
    setSelectedFile(null);
    reset();
  };

  return (
    <div className="space-y-3">
      <div
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          isDragging
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400'
        }`}
      >
        <Upload className="mb-2 h-8 w-8 text-gray-400" />
        <p className="text-sm font-medium text-gray-700">
          Drag and drop a file here, or{' '}
          <label className="cursor-pointer text-indigo-600 hover:underline">
            browse
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              className="sr-only"
              onChange={onFileChange}
              disabled={isUploading}
            />
          </label>
        </p>
        <p className="mt-1 text-xs text-gray-400">PDF, DOCX, TXT – up to 50 MB</p>
      </div>

      {selectedFile && (
        <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm">
          <FileText className="h-4 w-4 text-gray-500 flex-shrink-0" />
          <span className="flex-1 truncate text-gray-700">{selectedFile.name}</span>
          {!isUploading && (
            <button onClick={clearFile} className="text-gray-400 hover:text-gray-600">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {isUploading && (
        <div className="space-y-1">
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-2 rounded-full bg-indigo-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">Uploading and processing…</p>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}
    </div>
  );
};
