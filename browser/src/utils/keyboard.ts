/**
 * Keyboard navigation handler for Palimpsest.
 * Returns a cleanup function for useEffect teardown (React StrictMode safe).
 */

import { useViewStore } from '../stores/viewStore';
import { useProjectStore } from '../stores/projectStore';
import { useSearchStore } from '../stores/searchStore';
import { useTrackStore } from '../stores/trackStore';

export function setupKeyboardHandlers(): () => void {
  function handler(e: KeyboardEvent): void {
    const target = e.target as HTMLElement;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';

    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault();
      useSearchStore.getState().open();
      return;
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) {
      e.preventDefault();
      useViewStore.getState().zoomIn();
      return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === '-') {
      e.preventDefault();
      useViewStore.getState().zoomOut();
      return;
    }

    if (isInput && e.key !== 'Escape') return;

    const paragraphs = useProjectStore.getState().paragraphs;
    const maxIndex = paragraphs.length - 1;
    const search = useSearchStore.getState();

    switch (e.key) {
      case 'j':
      case 'ArrowDown': {
        e.preventDefault();
        const view = useViewStore.getState();
        const current = view.selectedParagraphIndex ?? -1;
        const next = Math.min(current + 1, maxIndex);
        view.setSelectedParagraphIndex(next);
        view.requestScrollToParagraph(next);
        break;
      }

      case 'k':
      case 'ArrowUp': {
        e.preventDefault();
        const view = useViewStore.getState();
        const current = view.selectedParagraphIndex ?? 1;
        const prev = Math.max(current - 1, 0);
        view.setSelectedParagraphIndex(prev);
        view.requestScrollToParagraph(prev);
        break;
      }

      case '/':
        if (!isInput) {
          e.preventDefault();
          search.open();
        }
        break;

      case 'Escape':
        if (search.isOpen) {
          search.close();
        } else {
          useViewStore.getState().selectAnnotation(null);
          useViewStore.getState().setSelectedParagraphIndex(null);
        }
        break;

      case 'd':
        if (!isInput) {
          useViewStore.getState().toggleTextHic();
        }
        break;

      case 'Enter': {
        if (!isInput && search.matches.length > 0) {
          e.preventDefault();
          if (e.shiftKey) {
            search.prevMatch();
          } else {
            search.nextMatch();
          }
        }
        break;
      }

      case '[':
        if (!isInput && search.matches.length > 0) {
          e.preventDefault();
          search.prevMatch();
        }
        break;

      case ']':
        if (!isInput && search.matches.length > 0) {
          e.preventDefault();
          search.nextMatch();
        }
        break;

      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
      case '6':
      case '7':
      case '8':
      case '9':
        if (!isInput) {
          e.preventDefault();
          useTrackStore.getState().toggleTrackByIndex(parseInt(e.key, 10));
        }
        break;

      case '0':
        if (!isInput) {
          e.preventDefault();
          const ts = useTrackStore.getState();
          const allVisible = Object.values(ts.tracks).every((t) => t.visible);
          const updated: Record<string, typeof ts.tracks[string]> = {};
          for (const [name, track] of Object.entries(ts.tracks)) {
            updated[name] = { ...track, visible: !allVisible };
          }
          ts.setTracks(updated);
        }
        break;

      case '?':
        if (!isInput) {
          e.preventDefault();
          useViewStore.getState().toggleHelp();
        }
        break;
    }
  }

  document.addEventListener('keydown', handler);
  return () => document.removeEventListener('keydown', handler);
}
