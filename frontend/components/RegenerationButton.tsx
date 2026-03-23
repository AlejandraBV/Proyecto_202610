import React from 'react';
import { RefreshCw } from 'lucide-react';

interface RegenerationButtonProps {
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  label?: string;
}

/**
 * Button that triggers a HITL content regeneration cycle.
 * No limit on the number of regeneration attempts.
 */
export const RegenerationButton: React.FC<RegenerationButtonProps> = ({
  onClick,
  loading = false,
  disabled = false,
  label = 'Regenerate',
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
    >
      <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
      {loading ? 'Regenerating…' : label}
    </button>
  );
};
