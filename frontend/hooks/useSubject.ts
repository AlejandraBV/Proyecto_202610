/**
 * useSubject — returns a function that translates a backend subject name
 * (always English in the DB) to the active UI language.
 *
 * Usage:
 *   const ts = useSubject();
 *   ts('Biology')  →  "Biology" | "Biología"
 *   ts('Unknown Subject')  →  "Unknown Subject"  (unchanged)
 */
import { useAppStore } from '@/store/appStore';
import { translateSubject } from '@/lib/translations';

export function useSubject() {
  const language = useAppStore((s) => s.language);
  return (name: string) => translateSubject(name, language);
}
