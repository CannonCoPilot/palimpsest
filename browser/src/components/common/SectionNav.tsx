/**
 * SectionNav — collapsible section navigation sidebar.
 * Lists section headings from the sections track; click to scroll.
 */

import { useMemo, useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useViewStore } from '../../stores/viewStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { Tooltip } from './Tooltip';

interface SectionEntry {
  index: number;
  heading: string;
  offset: number;
  paragraphIndex: number;
}

export default function SectionNav(): JSX.Element | null {
  const tracks = useProjectStore((s) => s.tracks);
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const requestScroll = useViewStore((s) => s.requestScrollToParagraph);
  const [collapsed, setCollapsed] = useState(true);

  const sections = useMemo((): SectionEntry[] => {
    const sectionAnns: W3CAnnotation[] = tracks['sections'] ?? [];
    if (sectionAnns.length === 0) return [];

    return sectionAnns
      .filter((a) => a.target.selector.start != null)
      .map((a) => {
        const offset = a.target.selector.start!;
        const heading =
          (a.body as Record<string, unknown>)['palimpsest:headingText'] as string ||
          a.body.value || '';
        const sectionIndex =
          (a.body as Record<string, unknown>)['palimpsest:sectionIndex'] as number ?? 0;
        const paraIdx = paragraphs.findIndex((p) => p.start <= offset && p.end > offset);
        return {
          index: sectionIndex,
          heading,
          offset,
          paragraphIndex: paraIdx >= 0 ? paraIdx : 0,
        };
      })
      .sort((a, b) => a.offset - b.offset);
  }, [tracks, paragraphs]);

  if (sections.length === 0) return null;

  return (
    <div style={{ borderBottom: '1px solid #ddd' }}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        style={{
          width: '100%',
          padding: '6px 12px',
          border: 'none',
          backgroundColor: '#fafafa',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.8em',
          fontWeight: 'bold',
          color: '#555',
        }}
      >
        <span>Sections ({sections.length})</span>
        <span>{collapsed ? '▶' : '▼'}</span>
      </button>
      {!collapsed && (
        <div style={{ maxHeight: '300px', overflowY: 'auto', padding: '4px 0' }}>
          {sections.map((s) => (
            <Tooltip key={s.index} content={s.heading} side="right">
              <div
                onClick={() => requestScroll(s.paragraphIndex)}
                style={{
                  padding: '4px 12px',
                  cursor: 'pointer',
                  fontSize: '0.8em',
                  color: '#333',
                  borderLeft: '2px solid transparent',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f0f7ff';
                  e.currentTarget.style.borderLeftColor = '#8e44ad';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.borderLeftColor = 'transparent';
                }}
              >
                {s.heading}
              </div>
            </Tooltip>
          ))}
        </div>
      )}
    </div>
  );
}
