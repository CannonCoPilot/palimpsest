/**
 * JSONL annotation adapter — loads W3C Web Annotation JSONL files.
 */

export interface W3CSelector {
  type: string;
  start?: number;
  end?: number;
  exact?: string;
  prefix?: string;
  suffix?: string;
}

export interface W3CBody {
  type: string;
  purpose?: string;
  value?: string;
  'palimpsest:lfoType'?: string;
  [key: string]: unknown;
}

export interface W3CTarget {
  source: string;
  selector: W3CSelector;
}

export interface W3CCreator {
  type: string;
  name: string;
}

export interface W3CAnnotation {
  '@context'?: unknown;
  type: string;
  id: string;
  body: W3CBody;
  target: W3CTarget;
  creator: W3CCreator;
  'palimpsest:confidence'?: number;
  'palimpsest:evidenceLevel'?: string;
}

export async function loadTrack(url: string): Promise<W3CAnnotation[]> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load track: ${response.status} ${response.statusText}`);
  }
  const text = await response.text();
  const annotations: W3CAnnotation[] = [];
  for (const line of text.trim().split('\n')) {
    if (line.length === 0) continue;
    try {
      annotations.push(JSON.parse(line) as W3CAnnotation);
    } catch {
      console.warn('Skipping malformed annotation line:', line.slice(0, 80));
    }
  }
  return annotations;
}
