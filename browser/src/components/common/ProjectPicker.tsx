/**
 * ProjectPicker — the app landing page, styled after the macOS Books app.
 *
 * A dark sidebar (search, nav, library sections, collections, user) beside a main
 * area with three views:
 *   - Home: a launchpad (hero, recent texts, and a grid of the suite's analysis
 *     tools). Selecting a tool sets a "pending tab" and routes to the library to
 *     pick a text, which then opens directly in that component.
 *   - Library ("All"): a grid of generated book covers. Texts without cover art get
 *     a deterministic gradient cover (title + author), mirroring Books' fallbacks.
 *   - Book Store: a launchpad of external sources (screenshot-thumbnail tiles that
 *     open sites for finding/searching more texts in a new tab).
 *
 * Import opens the 5-step ImportWizard as a full-screen Import view (not a modal).
 * Only consumer is AppLayout's no-project branch (CompareView has its own picker).
 */

import { useEffect, useMemo, useState, type ReactElement, type ReactNode } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useViewStore, type TabId } from '../../stores/viewStore';
import ImportWizard from '../import/ImportWizard';

interface ProjectEntry {
  id: string;
  title: string;
  author: string;
  word_count: number;
  cover?: string | null;
  source_file?: string;
}

// Curated rich/muted [from, to] gradient pairs — Books-like, not random HSL.
const COVER_PALETTE: ReadonlyArray<readonly [string, string]> = [
  ['#3a6ea5', '#1f3d63'], // blue
  ['#a85532', '#5e2f1b'], // rust
  ['#3a7d44', '#1d4427'], // green
  ['#7b4397', '#3f2152'], // purple
  ['#1f7a73', '#0d3e3a'], // teal
  ['#a83246', '#5c1a26'], // maroon
  ['#36507a', '#1c2a44'], // indigo
  ['#8a6d3b', '#4a3a1f'], // gold
  ['#4a5560', '#262d35'], // slate
  ['#9c3667', '#531d37'], // berry
];

function stableIndex(seed: string, mod: number): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0;
  return Math.abs(h) % mod;
}

// ── Inline SF-Symbol-ish icons (no icon dep in this project) ──────────────────
function Icon({ name, className = 'w-[18px] h-[18px]' }: { name: string; className?: string }): ReactElement {
  const glyphs: Record<string, ReactNode> = {
    search: (<><circle cx="11" cy="11" r="7" /><path d="m20 20-3.4-3.4" /></>),
    home: <path d="M3 10.8 12 3l9 7.8M5.5 9.3V20h13V9.3" />,
    store: <path d="M6 7V6a6 6 0 0 1 12 0v1M4 7h16l-1 13H5L4 7Z" />,
    library: <path d="M4 4h4v16H4zM10 4h4v16h-4zM17 5l3 .8L17 21l-3-.8" />,
    wantToRead: (<><circle cx="12" cy="12" r="9" /><path d="M12 8v5l3 2" /></>),
    finished: (<><circle cx="12" cy="12" r="9" /><path d="m8.5 12 2.5 2.5 4.5-5" /></>),
    book: <path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 0-2 2V4Zm0 0v16" />,
    doc: <path d="M7 3h7l4 4v14H7zM14 3v4h4" />,
    plus: <path d="M12 5v14M5 12h14" />,
    cloud: <path d="M7 18a4 4 0 0 1-.5-7.97A5 5 0 0 1 16 9.2 3.5 3.5 0 0 1 17 18H7Zm5-5v5m0 0-2-2m2 2 2-2" />,
    more: (<><circle cx="6" cy="12" r="1.4" /><circle cx="12" cy="12" r="1.4" /><circle cx="18" cy="12" r="1.4" /></>),
    columns: <path d="M4 4h7v16H4zM13 4h7v16h-7z" />,
    grid: (<><path d="M4 4h16v16H4z" /><path d="M4 9.3h16M4 14.6h16M9.3 4v16M14.6 4v16" /></>),
    users: (<><circle cx="9" cy="8" r="3" /><path d="M3.5 19a5.5 5.5 0 0 1 11 0" /><path d="M16 5.3a3 3 0 0 1 0 5.4M16.5 13.5a5.5 5.5 0 0 1 4 5.5" /></>),
    sliders: (<><path d="M4 8h9M17 8h3M4 16h3M11 16h9" /><circle cx="15" cy="8" r="2" /><circle cx="9" cy="16" r="2" /></>),
    compare: <path d="M4 5h16v14H4zM12 4v16" />,
    arrowRight: <path d="M5 12h14M13 6l6 6-6 6" />,
    globe: (<><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.6 2.7 2.6 15.3 0 18M12 3c-2.6 2.7-2.6 15.3 0 18" /></>),
    external: <path d="M14 4h6v6M19 5l-9 9M17 13v6H5V7h6" />,
  };
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6}
      strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {glyphs[name]}
    </svg>
  );
}

function NavRow({ icon, label, active = false, onClick }: {
  icon: string; label: string; active?: boolean; onClick?: () => void;
}): ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2.5 w-full px-2.5 py-[5px] rounded-md text-[13px] text-left transition-colors ${
        active
          ? 'bg-[#3a3a3d] text-white'
          : 'text-[#d6d6d8] hover:bg-white/[0.06]'
      }`}
    >
      <span className={active ? 'text-white' : 'text-[#9a9aa0]'}><Icon name={icon} /></span>
      <span className="truncate">{label}</span>
    </button>
  );
}

function SectionLabel({ children }: { children: ReactNode }): ReactElement {
  return (
    <div className="px-2.5 pt-4 pb-1 text-[11px] font-semibold uppercase tracking-wide text-[#8a8a90]">
      {children}
    </div>
  );
}

function BookCover({ project, onOpen, onReimport, onRefine, onDelete }: {
  project: ProjectEntry;
  onOpen: () => void;
  onReimport: () => void;
  onRefine: () => void;
  onDelete: () => void;
}): ReactElement {
  const [from, to] = COVER_PALETTE[stableIndex(project.id, COVER_PALETTE.length)];
  const [imgFailed, setImgFailed] = useState(false);
  const [menu, setMenu] = useState<null | 'main' | 'confirm-delete' | 'confirm-reimport'>(null);
  const showImage = Boolean(project.cover) && !imgFailed;

  useEffect(() => {
    if (!menu) return;
    const close = (): void => setMenu(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [menu]);

  return (
    <div className="group relative flex flex-col">
      <button type="button" onClick={onOpen} className="flex flex-col text-left focus:outline-none">
        <div
          className="relative w-full aspect-[2/3] rounded-[3px] overflow-hidden ring-1 ring-black/40
            shadow-[0_12px_22px_-8px_rgba(0,0,0,0.75)] transition-all duration-200
            group-hover:-translate-y-1 group-hover:shadow-[0_20px_34px_-8px_rgba(0,0,0,0.85)]
            group-focus-visible:ring-2 group-focus-visible:ring-[#0a84ff]"
          style={{ backgroundImage: `linear-gradient(155deg, ${from} 0%, ${to} 100%)` }}
        >
          {showImage ? (
            <img
              src={project.cover ?? ''}
              alt={`Cover of ${project.title}`}
              loading="lazy"
              onError={() => setImgFailed(true)}
              className="absolute inset-0 w-full h-full object-cover"
            />
          ) : (
            <>
              {/* spine highlight + page-edge shading for a printed-book feel */}
              <div className="absolute inset-y-0 left-0 w-[3px] bg-white/20" />
              <div className="absolute inset-y-0 left-[3px] w-[6px] bg-gradient-to-r from-white/10 to-transparent" />
              <div className="absolute inset-y-0 right-0 w-[5px] bg-gradient-to-l from-black/25 to-transparent" />
              <div className="absolute inset-0 flex flex-col justify-between px-3 pt-6 pb-4 text-center">
                <h3 className="font-[var(--font-serif)] text-white leading-tight text-[15px] [text-wrap:balance] break-words drop-shadow-[0_1px_2px_rgba(0,0,0,0.4)]">
                  {project.title}
                </h3>
                {project.author && (
                  <p className="text-white/80 text-[11px] uppercase tracking-wide break-words">
                    {project.author}
                  </p>
                )}
              </div>
            </>
          )}
        </div>
        <div className="mt-2">
          <span className="text-[12px] text-[#8e8e93] truncate">
            {project.word_count.toLocaleString()} words
          </span>
        </div>
      </button>

      {/* Overflow menu — sibling of the open-button (avoids nested buttons). */}
      <button
        type="button"
        aria-label={`More options for ${project.title}`}
        onClick={(e) => { e.stopPropagation(); setMenu((m) => (m ? null : 'main')); }}
        className="absolute top-1.5 right-1.5 z-10 w-7 h-7 rounded-full flex items-center justify-center
          bg-black/45 text-white/90 ring-1 ring-white/10 backdrop-blur-sm transition-opacity
          opacity-0 group-hover:opacity-100 focus:opacity-100 hover:bg-black/70"
      >
        <Icon name="more" className="w-4 h-4" />
      </button>

      {menu && (
        <div
          className="absolute top-9 right-1.5 z-20 min-w-[170px] rounded-lg bg-[#2a2a2c] ring-1 ring-white/15 shadow-xl py-1 text-[13px] text-[#e8e8ea]"
          onClick={(e) => e.stopPropagation()}
        >
          {menu === 'main' && (
            <>
              <button className="w-full text-left px-3 py-1.5 hover:bg-white/10" onClick={() => { setMenu(null); onOpen(); }}>Open</button>
              <button className="w-full text-left px-3 py-1.5 hover:bg-white/10" onClick={() => { setMenu(null); onRefine(); }}>Refine sections…</button>
              <button className="w-full text-left px-3 py-1.5 hover:bg-white/10" onClick={() => setMenu('confirm-reimport')}>Re-import…</button>
              <button className="w-full text-left px-3 py-1.5 hover:bg-white/10 text-[#ff453a]" onClick={() => setMenu('confirm-delete')}>Delete…</button>
            </>
          )}
          {menu === 'confirm-reimport' && (
            <div className="px-3 py-2 space-y-2">
              <p className="text-[12px] text-[#b0b0b6] leading-snug">Re-open the import wizard for this book? Finishing it replaces the current analysis.</p>
              <div className="flex gap-2">
                <button className="flex-1 px-2 py-1 rounded bg-[#0a84ff] hover:bg-[#0a78e6] text-white" onClick={() => { setMenu(null); onReimport(); }}>Re-import</button>
                <button className="flex-1 px-2 py-1 rounded bg-white/10 hover:bg-white/15" onClick={() => setMenu('main')}>Cancel</button>
              </div>
            </div>
          )}
          {menu === 'confirm-delete' && (
            <div className="px-3 py-2 space-y-2">
              <p className="text-[12px] text-[#b0b0b6] leading-snug">Delete this book and all of its analysis? This cannot be undone.</p>
              <div className="flex gap-2">
                <button className="flex-1 px-2 py-1 rounded bg-[#ff453a] hover:bg-[#e03e34] text-white" onClick={() => { setMenu(null); onDelete(); }}>Delete</button>
                <button className="flex-1 px-2 py-1 rounded bg-white/10 hover:bg-white/15" onClick={() => setMenu('main')}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Full-screen Import view (not a modal): a top-takeover that covers the picker
// so the wizard's steps have the whole viewport to work in. Esc returns to the
// library. No focus trap — this is a page, so native tab order is correct.
function ImportView({ onClose, initialSourceFile, resumeProjectId }: {
  onClose: () => void;
  initialSourceFile?: string;
  resumeProjectId?: string;
}): ReactElement {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent): void {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const heading = resumeProjectId ? 'Refine Sections & Masking' : 'Import a Text';

  return (
    <div className="fixed inset-0 z-[var(--z-overlay)] flex flex-col bg-[#1c1c1e] text-[#e8e8ea] font-[var(--font-sans)]">
      <header className="shrink-0 flex items-center gap-3 h-14 px-5 border-b border-black/40 bg-[#242426]">
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[13px] text-[#d6d6d8] hover:bg-white/[0.08] transition-colors"
        >
          <Icon name="arrowRight" className="w-4 h-4 rotate-180" /> Library
        </button>
        <h1 className="text-[15px] font-semibold text-white">{heading}</h1>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close import"
          className="ml-auto w-8 h-8 rounded-full text-[#8e8e93] hover:text-white hover:bg-white/10 text-base flex items-center justify-center"
        >
          ✕
        </button>
      </header>
      <div className="flex-1 min-h-0 overflow-y-auto">
        <ImportWizard initialSourceFile={initialSourceFile} resumeProjectId={resumeProjectId} />
      </div>
    </div>
  );
}

// The analysis components of the suite — each is a per-text tab (see viewStore).
const TOOLS: ReadonlyArray<{ tab: TabId; label: string; icon: string; desc: string }> = [
  { tab: 'reading', label: 'Reading', icon: 'book', desc: 'Linear text with annotation overlays' },
  { tab: 'browser', label: 'Browser', icon: 'columns', desc: 'Genome-browser-style track view' },
  { tab: 'texthic', label: 'TextHiC', icon: 'grid', desc: 'Self-similarity heatmap' },
  { tab: 'characters', label: 'Characters', icon: 'users', desc: 'Entity index & co-occurrence' },
  { tab: 'analysis', label: 'Analysis', icon: 'sliders', desc: 'Track computation & parameters' },
  { tab: 'compare', label: 'Compare', icon: 'compare', desc: 'Two-text alignment & diff' },
];

function HomeView({ projects, onOpenLibrary, onImport, onOpenProject, onLaunchTool, onReimport, onRefine, onDelete }: {
  projects: ProjectEntry[];
  onOpenLibrary: () => void;
  onImport: () => void;
  onOpenProject: (id: string) => void;
  onLaunchTool: (tab: TabId) => void;
  onReimport: (p: ProjectEntry) => void;
  onRefine: (p: ProjectEntry) => void;
  onDelete: (p: ProjectEntry) => void;
}): ReactElement {
  const hasProjects = projects.length > 0;
  return (
    <div className="px-10 pt-4 pb-16">
      {/* Hero */}
      <section className="rounded-2xl px-8 py-9 mb-9 ring-1 ring-white/10 bg-gradient-to-br from-[#2a2f63] to-[#13203b]">
        <h2 className="text-[26px] font-bold text-white">Welcome to Palimpsest</h2>
        <p className="mt-2 max-w-[580px] text-[14px] leading-relaxed text-white/70">
          A computational literary analysis suite — read, browse tracks, map self-similarity,
          explore characters, tune analyses, and compare editions. Pick a tool below or open a text to begin.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onOpenLibrary}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#0a84ff] text-white text-[13px] font-medium hover:bg-[#0a78e6] transition-colors"
          >
            <Icon name="library" className="w-4 h-4" /> Browse Library
          </button>
          <button
            type="button"
            onClick={onImport}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/10 text-white text-[13px] font-medium hover:bg-white/15 transition-colors"
          >
            <Icon name="plus" className="w-4 h-4" /> Import a Text
          </button>
        </div>
      </section>

      {/* Your texts */}
      <section className="mb-10">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[17px] font-semibold text-white">Your texts</h2>
          {hasProjects && (
            <button
              type="button"
              onClick={onOpenLibrary}
              className="flex items-center gap-1 text-[13px] text-[#8e8e93] hover:text-white transition-colors"
            >
              See all <Icon name="arrowRight" className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        {hasProjects ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-x-6 gap-y-7">
            {projects.slice(0, 12).map((p) => (
              <BookCover
                key={p.id}
                project={p}
                onOpen={() => onOpenProject(p.id)}
                onReimport={() => onReimport(p)}
                onRefine={() => onRefine(p)}
                onDelete={() => onDelete(p)}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-xl ring-1 ring-white/10 bg-[#242426] px-6 py-8 text-center">
            <p className="text-[14px] text-[#8e8e93] mb-3">No texts yet — import one to start analyzing.</p>
            <button
              type="button"
              onClick={onImport}
              className="px-4 py-2 rounded-md bg-[#0a84ff] text-white text-[13px] hover:bg-[#0a78e6]"
            >
              Import a text
            </button>
          </div>
        )}
      </section>

      {/* Analysis tools — launchpad into each component */}
      <section>
        <h2 className="text-[17px] font-semibold text-white mb-1">Analysis tools</h2>
        <p className="text-[13px] text-[#8e8e93] mb-4">
          {hasProjects ? 'Open any tool, then choose a text to analyze.' : 'Import a text to unlock these tools.'}
        </p>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-4">
          {TOOLS.map((t) => (
            <button
              key={t.tab}
              type="button"
              onClick={() => onLaunchTool(t.tab)}
              className="group flex items-start gap-3 rounded-xl px-4 py-4 text-left bg-[#242426] ring-1 ring-white/10
                hover:bg-[#2a2a2c] hover:ring-white/25 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]"
            >
              <span className="mt-0.5 text-[#5a8dee] group-hover:text-[#0a84ff] transition-colors">
                <Icon name={t.icon} className="w-5 h-5" />
              </span>
              <span className="min-w-0">
                <span className="block text-[14px] font-medium text-white">{t.label}</span>
                <span className="block text-[12px] text-[#8e8e93] mt-0.5">{t.desc}</span>
              </span>
              <span className="ml-auto self-center text-[#5a5a5f] opacity-0 group-hover:opacity-100 transition-opacity">
                <Icon name="arrowRight" className="w-4 h-4" />
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

// External sources for finding more texts to import. The Book Store view is a
// launchpad of these; each tile previews the site via a header screenshot
// (browser/public/store/*.png) with a tinted gradient fallback.
interface StoreSite {
  name: string;
  url: string;
  domain: string;
  desc: string;
  thumb: string;
  tint: readonly [string, string];
}

const STORES: ReadonlyArray<StoreSite> = [
  {
    name: 'Early Christian Writings',
    url: 'https://www.earlychristianwritings.com/',
    domain: 'earlychristianwritings.com',
    desc: 'Gospels, epistles & patristic texts with translations and commentary',
    thumb: '/store/early-christian-writings.png',
    tint: ['#8a6d3b', '#4a3a1f'],
  },
  {
    name: 'Internet Sacred Text Archive',
    url: 'https://sacred-texts.com/cat/index.htm',
    domain: 'sacred-texts.com',
    desc: 'Vast archive of religious, mythological & folklore texts',
    thumb: '/store/sacred-texts.png',
    tint: ['#1f7a73', '#0d3e3a'],
  },
  {
    name: "Anna's Archive",
    url: 'https://annas-archive.gl/',
    domain: 'annas-archive.gl',
    desc: 'Search engine for books, papers & library collections',
    thumb: '/store/annas-archive.png',
    tint: ['#36507a', '#1c2a44'],
  },
];

function StoreTile({ site }: { site: StoreSite }): ReactElement {
  const [imgFailed, setImgFailed] = useState(false);
  return (
    <a
      href={site.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-xl overflow-hidden bg-[#242426] ring-1 ring-white/10 transition-all duration-200
        shadow-[0_10px_22px_-10px_rgba(0,0,0,0.7)] hover:ring-white/25 hover:-translate-y-0.5
        hover:shadow-[0_18px_30px_-10px_rgba(0,0,0,0.85)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0a84ff]"
    >
      <div
        className="relative aspect-[16/9] overflow-hidden"
        style={{ backgroundImage: `linear-gradient(155deg, ${site.tint[0]}, ${site.tint[1]})` }}
      >
        {!imgFailed ? (
          <img
            src={site.thumb}
            alt={`${site.name} homepage`}
            loading="lazy"
            onError={() => setImgFailed(true)}
            className="absolute inset-0 w-full h-full object-cover object-top transition-transform duration-300 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center px-4">
            <span className="font-[var(--font-serif)] text-white/90 text-[18px] text-center [text-wrap:balance]">
              {site.name}
            </span>
          </div>
        )}
        <div className="absolute inset-0 ring-1 ring-inset ring-white/10 pointer-events-none" />
      </div>
      <div className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="text-[14px] font-medium text-white truncate">{site.name}</span>
          <span className="shrink-0 text-[#8e8e93] opacity-0 group-hover:opacity-100 transition-opacity">
            <Icon name="external" className="w-3.5 h-3.5" />
          </span>
        </div>
        <p className="text-[12px] text-[#8e8e93] mt-0.5 leading-snug">{site.desc}</p>
        <p className="text-[11px] text-[#5a8dee] mt-1.5">{site.domain}</p>
      </div>
    </a>
  );
}

function StoreView(): ReactElement {
  return (
    <div className="px-10 pt-4 pb-16">
      <p className="text-[13px] text-[#8e8e93] mb-5 max-w-[640px]">
        Browse external libraries and search engines for more texts to import. Links open in a new tab.
      </p>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-5">
        {STORES.map((s) => (
          <StoreTile key={s.url} site={s} />
        ))}
      </div>
    </div>
  );
}

export default function ProjectPicker(): ReactElement {
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [reimportFile, setReimportFile] = useState<string | null>(null);
  const [resumeProject, setResumeProject] = useState<string | null>(null);
  const [page, setPage] = useState<'home' | 'library' | 'store'>('home');
  const [pendingTab, setPendingTab] = useState<TabId | null>(null);
  const loadProject = useProjectStore((s) => s.loadProject);

  useEffect(() => {
    fetch('/api/projects')
      .then((r) => {
        if (!r.ok) throw new Error('Failed to fetch projects');
        return r.json();
      })
      .then((data: ProjectEntry[]) => {
        setProjects(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Open a text. If a tool was chosen on Home, land directly in that component.
  function handleSelect(id: string, tab: TabId | null = pendingTab): void {
    if (tab) useViewStore.getState().setActiveTab(tab);
    const url = new URL(window.location.href);
    url.searchParams.set('project', id);
    window.history.pushState({}, '', url.toString());
    loadProject('', id);
    setPendingTab(null);
  }

  function goHome(): void {
    setPage('home');
    setPendingTab(null);
    setQuery('');
  }

  function goLibrary(): void {
    setPage('library');
  }

  function goStore(): void {
    setPage('store');
    setPendingTab(null);
    setQuery('');
  }

  // Launch a tool from Home: with texts, route to the library to pick one (the
  // chosen tool becomes the pending tab); with none, prompt to import first.
  function launchTool(tab: TabId): void {
    if (projects.length === 0) {
      setShowImport(true);
      return;
    }
    setPendingTab(tab);
    setPage('library');
  }

  // Delete a project (BookCover already confirmed in its menu).
  async function handleDelete(p: ProjectEntry): Promise<void> {
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(p.id)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setProjects((prev) => prev.filter((x) => x.id !== p.id));
    } catch (err) {
      window.alert(`Could not delete “${p.title}”: ${err instanceof Error ? err.message : 'unknown error'}`);
    }
  }

  // Re-import: re-open the wizard pre-loaded with this book's source file
  // (BookCover already confirmed). Replaces the analysis only on completion.
  function handleReimport(p: ProjectEntry): void {
    if (!p.source_file) {
      window.alert(`“${p.title}” has no recorded source file to re-import.`);
      return;
    }
    setReimportFile(p.source_file);
    setShowImport(true);
  }

  // Refine (#11/#26): re-open the wizard on an existing project at the Detect
  // step to re-run sections/masking without re-ingesting the source file.
  function handleRefine(p: ProjectEntry): void {
    setResumeProject(p.id);
    setShowImport(true);
  }

  function closeImport(): void {
    setShowImport(false);
    setReimportFile(null);
    setResumeProject(null);
  }

  const pendingToolLabel = pendingTab ? TOOLS.find((t) => t.tab === pendingTab)?.label : null;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter(
      (p) => p.title.toLowerCase().includes(q) || p.author.toLowerCase().includes(q),
    );
  }, [projects, query]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#1c1c1e] text-[#e8e8ea] font-[var(--font-sans)]">
      {/* ── Sidebar ───────────────────────────────────────────────────────── */}
      <aside className="w-[232px] shrink-0 flex flex-col bg-[#242426] border-r border-black/40">
        <div className="px-3 pt-6 pb-1">
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-black/25 focus-within:ring-1 focus-within:ring-[#0a84ff]">
            <span className="text-[#9a9aa0]"><Icon name="search" className="w-[15px] h-[15px]" /></span>
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (e.target.value) setPage('library');
              }}
              placeholder="Search"
              className="bg-transparent outline-none text-[13px] text-white placeholder:text-[#8a8a90] w-full"
            />
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-1">
          <NavRow icon="home" label="Home" active={page === 'home'} onClick={goHome} />
          <NavRow icon="store" label="Book Store" active={page === 'store'} onClick={goStore} />

          <SectionLabel>Library</SectionLabel>
          <NavRow icon="library" label="All" active={page === 'library'} onClick={goLibrary} />
          <NavRow icon="wantToRead" label="Started" />
          <NavRow icon="finished" label="Finished" />
          <NavRow icon="book" label="Novels" />
          <NavRow icon="globe" label="Translations" />
          <NavRow icon="doc" label="Papers" />
          <NavRow icon="users" label="Scholars" />

          <SectionLabel>My Collections</SectionLabel>
          <NavRow icon="plus" label="New Collection" onClick={() => setShowImport(true)} />
        </nav>

        <div className="flex items-center gap-2.5 px-4 py-3 border-t border-white/10">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#5a8dee] to-[#7b4397] flex items-center justify-center text-[11px] font-semibold text-white">
            NC
          </div>
          <span className="text-[13px] text-[#d6d6d8] truncate">Nathaniel Cannon</span>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <div className="flex items-start justify-between px-10 pt-6">
          <h1 className="text-[34px] font-bold tracking-tight text-white">
            {page === 'home' ? 'Home' : page === 'store' ? 'Book Store' : 'All'}
          </h1>
          <button
            type="button"
            onClick={() => setShowImport(true)}
            className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[13px] text-[#d6d6d8] hover:bg-white/[0.08] transition-colors"
            title="Import a text"
          >
            <Icon name="plus" className="w-4 h-4" /> Import
          </button>
        </div>

        {page === 'home' ? (
          <HomeView
            projects={projects}
            onOpenLibrary={goLibrary}
            onImport={() => setShowImport(true)}
            onOpenProject={(id) => handleSelect(id, null)}
            onLaunchTool={launchTool}
            onReimport={handleReimport}
            onRefine={handleRefine}
            onDelete={handleDelete}
          />
        ) : page === 'store' ? (
          <StoreView />
        ) : (
          <div className="px-10 pb-16 pt-4">
            {pendingToolLabel && (
              <div className="mb-5 flex items-center justify-between gap-3 rounded-lg px-4 py-2.5 bg-[#0a84ff]/15 ring-1 ring-[#0a84ff]/40">
                <span className="text-[13px] text-[#d6e7ff]">
                  Choose a text to open in <strong className="text-white">{pendingToolLabel}</strong>.
                </span>
                <button
                  type="button"
                  onClick={() => setPendingTab(null)}
                  className="text-[12px] text-[#8e8e93] hover:text-white transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}

            {loading && <div className="text-[#8e8e93] text-[14px]">Loading library…</div>}

            {error && (
              <div className="text-[#ff6b6b] text-[14px]">
                Could not load library: {error}
              </div>
            )}

            {!loading && !error && projects.length === 0 && (
              <div className="flex flex-col items-center justify-center text-center mt-24 text-[#8e8e93]">
                <p className="text-[15px] mb-4">Your library is empty.</p>
                <button
                  type="button"
                  onClick={() => setShowImport(true)}
                  className="px-4 py-2 rounded-md bg-[#0a84ff] text-white text-[13px] hover:bg-[#0a78e6]"
                >
                  Import a text
                </button>
              </div>
            )}

            {!loading && !error && projects.length > 0 && (
              filtered.length === 0 ? (
                <div className="text-[#8e8e93] text-[14px]">No titles match “{query}”.</div>
              ) : (
                <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-x-7 gap-y-8">
                  {filtered.map((p) => (
                    <BookCover
                      key={p.id}
                      project={p}
                      onOpen={() => handleSelect(p.id)}
                      onReimport={() => handleReimport(p)}
                      onRefine={() => handleRefine(p)}
                      onDelete={() => handleDelete(p)}
                    />
                  ))}
                </div>
              )
            )}
          </div>
        )}
      </main>

      {showImport && (
        <ImportView
          onClose={closeImport}
          initialSourceFile={reimportFile ?? undefined}
          resumeProjectId={resumeProject ?? undefined}
        />
      )}
    </div>
  );
}
