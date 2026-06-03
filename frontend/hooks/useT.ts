/**
 * useT — returns a translator bound to the active UI language.
 *
 * Usage:
 *   const T = useT();
 *   <span>{T(tr.sidebar.newChat)}</span>
 */
import { useAppStore } from '@/store/appStore';
import { t } from '@/lib/translations';

export function useT() {
  const language = useAppStore((s) => s.language);
  return (entry: { en: string; es: string }) => t(entry, language);
}
