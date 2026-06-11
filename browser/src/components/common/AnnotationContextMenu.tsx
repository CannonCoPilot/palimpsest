import * as ContextMenu from '@radix-ui/react-context-menu';
import type { ReactNode } from 'react';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore } from '../../stores/projectStore';
import { useSearchStore } from '../../stores/searchStore';

interface Props {
  annotation: W3CAnnotation;
  children: ReactNode;
}

export default function AnnotationContextMenu({ annotation, children }: Props) {
  const sel = annotation.target.selector;
  const typeName = annotation.body.type.replace('palimpsest:', '');

  const handleCopyText = () => {
    const text = useProjectStore.getState().referenceText;
    if (sel.start != null && sel.end != null) {
      navigator.clipboard.writeText(text.slice(sel.start, sel.end));
    }
  };

  const handleNavigate = () => {
    if (sel.start == null) return;
    const paragraphs = useProjectStore.getState().paragraphs;
    const paraIdx = paragraphs.findIndex((p) => p.start <= sel.start! && p.end > sel.start!);
    if (paraIdx >= 0) {
      useViewStore.getState().setSelectedParagraphIndex(paraIdx);
      useViewStore.getState().requestScrollToParagraph(paraIdx);
    }
  };

  const handleSelect = () => {
    useViewStore.getState().selectAnnotation(annotation);
  };

  const handleShowAllMentions = () => {
    const value = annotation.body.value;
    const canonicalName = (annotation.body as Record<string, unknown>)['palimpsest:canonicalName'] as string | undefined;
    const searchTerm = canonicalName || value || '';
    if (searchTerm) {
      useViewStore.getState().setActiveTab('reading');
      const { referenceText, paragraphs } = useProjectStore.getState();
      const search = useSearchStore.getState();
      search.open();
      search.setQuery(searchTerm, referenceText, paragraphs);
    }
  };

  return (
    <ContextMenu.Root>
      <ContextMenu.Trigger className="inline">{children}</ContextMenu.Trigger>
      <ContextMenu.Portal>
        <ContextMenu.Content
          className="min-w-[160px] rounded-[var(--radius-md)] bg-[var(--color-bg)] border border-[var(--color-border)] shadow-[var(--shadow-popover)] py-1 z-[var(--z-popover)] text-sm font-[var(--font-sans)] animate-[tooltip-fade-in_var(--duration-fast)_ease-out]"
        >
          <ContextMenu.Label className="px-3 py-1 text-[0.75em] text-[var(--color-text-muted)] font-semibold">
            {typeName}
          </ContextMenu.Label>
          <ContextMenu.Separator className="h-px bg-[var(--color-border-subtle)] my-0.5" />
          <ContextMenu.Item
            className="px-3 py-1.5 text-[var(--color-text)] cursor-pointer hover:bg-[var(--color-bg-muted)] outline-none data-[highlighted]:bg-[var(--color-bg-muted)]"
            onSelect={handleSelect}
          >
            View details
          </ContextMenu.Item>
          <ContextMenu.Item
            className="px-3 py-1.5 text-[var(--color-text)] cursor-pointer hover:bg-[var(--color-bg-muted)] outline-none data-[highlighted]:bg-[var(--color-bg-muted)]"
            onSelect={handleCopyText}
          >
            Copy text
          </ContextMenu.Item>
          <ContextMenu.Item
            className="px-3 py-1.5 text-[var(--color-text)] cursor-pointer hover:bg-[var(--color-bg-muted)] outline-none data-[highlighted]:bg-[var(--color-bg-muted)]"
            onSelect={handleNavigate}
          >
            Navigate to position
          </ContextMenu.Item>
          <ContextMenu.Separator className="h-px bg-[var(--color-border-subtle)] my-0.5" />
          <ContextMenu.Item
            className="px-3 py-1.5 text-[var(--color-text)] cursor-pointer hover:bg-[var(--color-bg-muted)] outline-none data-[highlighted]:bg-[var(--color-bg-muted)]"
            onSelect={handleShowAllMentions}
          >
            Show all mentions
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu.Root>
  );
}
