import React from 'react';
import ReactMarkdown from 'react-markdown';
import { GeneratedContent } from '@/types';

interface ContentPreviewProps {
  content: GeneratedContent;
  className?: string;
}

/** Renders generated academic content with markdown support. */
export const ContentPreview: React.FC<ContentPreviewProps> = ({ content, className = '' }) => {
  return (
    <div className={`rounded-lg border border-gray-200 bg-white p-6 shadow-sm ${className}`}>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{content.title}</h2>
          <p className="text-sm text-gray-500">
            {content.contentType} &bull; Version {content.version}
          </p>
        </div>
        {content.confidenceScore !== undefined && (
          <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
            Score: {Math.round(content.confidenceScore * 100)}%
          </span>
        )}
      </div>
      <div className="prose prose-sm max-w-none text-gray-700">
        <ReactMarkdown>{content.content}</ReactMarkdown>
      </div>
    </div>
  );
};
