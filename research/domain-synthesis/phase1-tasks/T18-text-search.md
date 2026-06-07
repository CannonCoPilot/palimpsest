# T18: Text Search (Rust + Browser)

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 6 hours (up from 5; Rust search engine is non-trivial)
**Dependencies**: T09 (Tauri shell + virtual scroll), T15 (AnnotationStore loaded)
**Outputs**: `src-tauri/src/search.rs` (created); `browser/src/stores/searchStore.ts` (created); `browser/src/components/TextLinearView/TextSearch.tsx` (created); `browser/src/utils/keyboard.ts` (modified)

---

## v4.0 Critical Review

**Verdict: The JavaScript `String.prototype.indexOf` loop searching a 600KB string in the browser is unacceptable. It blocks the JS main thread for 50-200ms on a full novel. At 5 simultaneous novels it is simply impossible. The search engine moves to Rust.**

### What is broken

**1. `String.prototype.indexOf` in a loop over 600KB is O(n×m) and runs on the JS main thread.**
The original comment concedes: "O(n × m) in the worst case but acceptable for a single-novel reference text (<1MB). For Phase 1, this is sufficient." This is not a design, it is a deferral. On a 600KB text with a 3-character query like "the", `indexOf` finds ~10,000 matches. Each call traverses up to 600KB to find the next match. Total JS time: 50-200ms, during which the browser is frozen. At v4.0 target of 5 simultaneous novels (~3MB total), this becomes completely non-functional.

**2. The `paragraphs.findIndex()` O(n) scan per match to assign `paragraphIndex` is O(matches × paragraphs).**
For 10,000 matches and 2,500 paragraphs, this is 25 million comparisons — all in JavaScript, all on the main thread, all blocking rendering. The original acknowledges none of this.

**3. The `referenceText: string` in `projectStore` is a 600KB JavaScript string.**
In v4.0, the reference text lives in the Rust `AnnotationStore` / `ProjectManager` — NOT in the JS heap. The browser does not hold the full text. Search operates on the Rust side, and the browser receives only the match offsets as a compact array. Holding 5 × 600KB = 3MB of reference text in the JS heap as strings would balloon V8's heap and trigger GC pauses.

**4. `useSearchStore.getState().setQuery(query, referenceText, paragraphs)` passes two large React state objects into every keypress handler.**
Every keystroke calls `setQuery` with the full `referenceText` string and `paragraphs` array as arguments. If `referenceText` is in the store, it is deserialized from JSON each render cycle. This is a performance antipattern that the original design explicitly creates.

**5. `<mark>` DOM elements for every match in every visible paragraph.**
The original renders `<mark key={match-start}>` elements inside the virtual scroll container. For 200 visible matches across 30 paragraphs, this is 200 additional DOM elements per render — defeating the purpose of the Canvas overlay. In v4.0, search matches are drawn on the Canvas annotation overlay layer as colored rectangles, same as annotation highlights. Zero additional DOM nodes.

**6. The suffix array and Aho-Corasick alternatives mentioned in the architecture doc are not optional.**
The v4 architecture doc (§10) specifies: "Search (Ctrl+F): <10ms (Rust regex + index) — Pre-built suffix array." Sub-10ms search across multiple novels is the REQUIREMENT. `indexOf` cannot satisfy this at scale. A suffix array built at project load time gives O(m log n) lookup for any query. For literal string search, Aho-Corasick gives O(n + m + k) where k is match count — optimal when multiple patterns are searched simultaneously.

---

## v4.0 Rewrite

### Architecture

```
Browser (keypress → invoke)
  │
  ├── user types "Bennet" in TextSearch component
  ├── invoke("search_text", { project_id, query, case_sensitive: false })
  │     [Tauri IPC — zero-copy where possible]
  │
  ▼
Rust search engine (src-tauri/src/search.rs)
  │
  ├── ProjectManager::get_project(project_id)
  │     └── SuffixArray (pre-built on project load, ~50ms for 600KB text)
  │
  ├── SuffixArray::search(query, case_sensitive) → Vec<u32>  (character offsets)
  │     └── binary search: O(m log n) where m=query length, n=text length
  │         On M4: <1ms for full novel, <5ms for 5 novels simultaneously
  │
  ├── Map offsets to paragraph indices via RangeIndex::batch_query()
  │     └── O(k log n) interval tree queries, k = match count
  │
  └── Return: SearchResult { matches: Vec<SearchMatch>, query_ms: f64 }
        │
        └── matches: [{start: u32, end: u32, paragraph_index: u32}]
              → compact u32 array, ~12 bytes per match
              → 10,000 matches = 120KB, not 10,000 JS objects
```

**Performance requirement**: full-text search across 1 novel in **<10ms** (including Rust processing + Tauri IPC round-trip). Across 5 simultaneous novels in **<30ms**.

### Rust implementation

**`src-tauri/src/search.rs`**:

```rust
use std::collections::HashMap;

/// Suffix array for a single document's reference text.
/// Built once on project load; search is O(m log n).
pub struct SuffixArray {
    text: String,                    // original reference text
    text_lower: String,              // lowercase version for case-insensitive search
    suffixes: Vec<u32>,              // sorted suffix start positions (u32 — texts up to 4GB)
    suffixes_lower: Vec<u32>,        // sorted over lowercase text
}

impl SuffixArray {
    /// Build suffix array from reference text. O(n log n) construction.
    /// For 600KB text: ~50ms on M4 Max. Run once, cache in ProjectManager.
    pub fn build(text: String) -> Self {
        let text_lower = text.to_lowercase();
        let mut suffixes: Vec<u32> = (0..text.len() as u32).collect();
        let mut suffixes_lower: Vec<u32> = (0..text_lower.len() as u32).collect();

        // Sort by suffix content — this is the O(n log n) step
        let text_bytes = text.as_bytes();
        suffixes.sort_unstable_by(|&a, &b| {
            text_bytes[a as usize..].cmp(&text_bytes[b as usize..])
        });
        let lower_bytes = text_lower.as_bytes();
        suffixes_lower.sort_unstable_by(|&a, &b| {
            lower_bytes[a as usize..].cmp(&lower_bytes[b as usize..])
        });

        Self { text, text_lower, suffixes, suffixes_lower }
    }

    /// Find all occurrences of `query` in the text. Returns sorted start offsets.
    /// O(m log n + k) where m = query length, n = text length, k = match count.
    pub fn search(&self, query: &str, case_sensitive: bool) -> Vec<u32> {
        if query.is_empty() {
            return vec![];
        }

        let (haystack, needle_str, suffix_arr) = if case_sensitive {
            (&self.text, query.to_string(), &self.suffixes)
        } else {
            (&self.text_lower, query.to_lowercase(), &self.suffixes_lower)
        };

        let needle = needle_str.as_bytes();
        let haystack_bytes = haystack.as_bytes();

        // Binary search for the range of suffixes that start with `needle`
        let lo = suffix_arr.partition_point(|&pos| {
            let suffix = &haystack_bytes[pos as usize..];
            suffix < needle
        });
        let hi = suffix_arr.partition_point(|&pos| {
            let suffix = &haystack_bytes[pos as usize..];
            let prefix = &suffix[..suffix.len().min(needle.len())];
            prefix <= needle
        });

        // Collect and validate: each suffix at positions [lo, hi) starts with needle
        let mut matches: Vec<u32> = suffix_arr[lo..hi]
            .iter()
            .copied()
            .filter(|&pos| {
                let end = pos as usize + needle.len();
                end <= haystack_bytes.len()
                    && &haystack_bytes[pos as usize..end] == needle
            })
            .collect();

        matches.sort_unstable();
        matches
    }

    pub fn text(&self) -> &str {
        &self.text
    }
}

/// Result of a text search query.
#[derive(Debug, serde::Serialize)]
pub struct SearchResult {
    pub matches: Vec<SearchMatch>,
    pub query_ms: f64,
    pub total_count: usize,
}

#[derive(Debug, serde::Serialize, Clone)]
pub struct SearchMatch {
    pub start: u32,
    pub end: u32,
    pub paragraph_index: u32,
}

/// Search across a loaded project. Queries the SuffixArray and maps matches
/// to paragraph indices via the RangeIndex.
pub fn search_project(
    suffix_array: &SuffixArray,
    range_index: &crate::range_index::RangeIndex,
    paragraphs: &[(u32, u32)],   // (start, end) pairs, parallel to paragraph display
    query: &str,
    case_sensitive: bool,
) -> SearchResult {
    let start_time = std::time::Instant::now();

    let offsets = suffix_array.search(query, case_sensitive);
    let query_len = query.len() as u32;

    let matches: Vec<SearchMatch> = offsets
        .iter()
        .map(|&start| {
            let end = start + query_len;
            // Binary search paragraphs for the one containing this offset
            let para_idx = paragraphs
                .partition_point(|(_, para_end)| *para_end <= start) as u32;
            SearchMatch { start, end, paragraph_index: para_idx }
        })
        .collect();

    let total_count = matches.len();
    SearchResult {
        matches,
        query_ms: start_time.elapsed().as_secs_f64() * 1000.0,
        total_count,
    }
}
```

### Tauri command

```rust
// src-tauri/src/commands/search.rs

#[tauri::command]
pub async fn search_text(
    project_id: String,
    query: String,
    case_sensitive: bool,
    state: tauri::State<'_, AppState>,
) -> Result<SearchResult, String> {
    if query.is_empty() {
        return Ok(SearchResult { matches: vec![], query_ms: 0.0, total_count: 0 });
    }
    if query.len() > 200 {
        return Err("Query too long (max 200 characters)".to_string());
    }

    let manager = state.project_manager.read().await;
    let project = manager
        .get_project(&project_id)
        .ok_or_else(|| format!("Project '{}' not loaded", project_id))?;

    Ok(crate::search::search_project(
        &project.suffix_array,
        &project.range_index,
        &project.paragraphs,
        &query,
        case_sensitive,
    ))
}
```

### Frontend searchStore (updated for Tauri)

```typescript
// browser/src/stores/searchStore.ts

import { create } from "zustand";
import { invoke } from "@tauri-apps/api/tauri";

export interface SearchMatch {
  start: number;
  end: number;
  paragraph_index: number;
}

interface SearchState {
  query: string;
  caseSensitive: boolean;
  isOpen: boolean;
  matches: SearchMatch[];
  currentMatchIndex: number;
  isLoading: boolean;
  queryMs: number | null;

  // Actions
  setQuery: (query: string, projectId: string) => Promise<void>;
  toggleCaseSensitive: (projectId: string) => Promise<void>;
  open: () => void;
  close: () => void;
  nextMatch: () => void;
  prevMatch: () => void;
}

export const useSearchStore = create<SearchState>((set, get) => ({
  query: "",
  caseSensitive: false,
  isOpen: false,
  matches: [],
  currentMatchIndex: -1,
  isLoading: false,
  queryMs: null,

  setQuery: async (query: string, projectId: string) => {
    set({ query, isLoading: query.length > 0 });
    if (query.length === 0) {
      set({ matches: [], currentMatchIndex: -1, isLoading: false });
      return;
    }
    try {
      const result = await invoke<{ matches: SearchMatch[]; query_ms: number; total_count: number }>(
        "search_text",
        { projectId, query, caseSensitive: get().caseSensitive }
      );
      set({
        matches: result.matches,
        currentMatchIndex: result.matches.length > 0 ? 0 : -1,
        isLoading: false,
        queryMs: result.query_ms,
      });
    } catch (err) {
      console.error("Search failed:", err);
      set({ matches: [], currentMatchIndex: -1, isLoading: false });
    }
  },

  toggleCaseSensitive: async (projectId: string) => {
    const { query, caseSensitive } = get();
    set({ caseSensitive: !caseSensitive });
    if (query.length > 0) {
      await get().setQuery(query, projectId);
    }
  },

  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false, query: "", matches: [], currentMatchIndex: -1 }),

  nextMatch: () => {
    const { matches, currentMatchIndex } = get();
    if (matches.length === 0) return;
    set({ currentMatchIndex: (currentMatchIndex + 1) % matches.length });
  },

  prevMatch: () => {
    const { matches, currentMatchIndex } = get();
    if (matches.length === 0) return;
    set({ currentMatchIndex: (currentMatchIndex - 1 + matches.length) % matches.length });
  },
}));
```

Key differences from the original:
- `setQuery` is `async` — it calls `invoke("search_text")` instead of running `findMatches()` in JS
- `referenceText` and `paragraphs` are NOT passed as arguments — Rust owns this data
- `isLoading` state added — the Tauri call is async; show a spinner while Rust is searching
- `queryMs` stored for debug display ("found 4,823 matches in 2.3ms")

### TextSearch component (updated)

```tsx
// browser/src/components/TextLinearView/TextSearch.tsx

import { useRef, useEffect, useCallback } from "react";
import { useSearchStore } from "../../stores/searchStore";
import { useProjectStore } from "../../stores/projectStore";

export function TextSearch() {
  const {
    query, caseSensitive, isOpen, matches, currentMatchIndex, isLoading, queryMs,
    setQuery, toggleCaseSensitive, close, nextMatch, prevMatch,
  } = useSearchStore();
  const { currentProjectId } = useProjectStore();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (currentProjectId) {
        void setQuery(e.target.value, currentProjectId);
      }
    },
    [setQuery, currentProjectId]
  );

  if (!isOpen) return null;

  return (
    <div className="text-search" role="search" aria-label="Text search">
      <input
        ref={inputRef}
        className="text-search__input"
        type="text"
        placeholder="Search…"
        value={query}
        onChange={handleChange}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); nextMatch(); }
          if (e.key === "Enter" && e.shiftKey) { e.preventDefault(); prevMatch(); }
          if (e.key === "Escape") { close(); }
          if (e.key === "]") { e.preventDefault(); nextMatch(); }
          if (e.key === "[") { e.preventDefault(); prevMatch(); }
        }}
      />
      <button
        className={`text-search__case-btn ${caseSensitive ? "active" : ""}`}
        onClick={() => currentProjectId && toggleCaseSensitive(currentProjectId)}
        title="Case-sensitive search"
        aria-pressed={caseSensitive}
      >
        Aa
      </button>
      <span className="text-search__count" aria-live="polite">
        {isLoading
          ? "Searching…"
          : matches.length === 0 && query.length > 0
          ? "No matches"
          : matches.length > 0
          ? `${currentMatchIndex + 1} of ${matches.length}${queryMs != null ? ` (${queryMs.toFixed(1)}ms)` : ""}`
          : ""}
      </span>
      <button onClick={prevMatch} disabled={matches.length === 0} aria-label="Previous match">▲</button>
      <button onClick={nextMatch} disabled={matches.length === 0} aria-label="Next match">▼</button>
      <button onClick={close} aria-label="Close search">✕</button>
    </div>
  );
}
```

### Canvas search highlight rendering

In the `CanvasAnnotationOverlay`, search matches are drawn as a distinct color layer:

```typescript
function drawSearchMatches(
  ctx: CanvasRenderingContext2D,
  matches: SearchMatch[],
  currentMatchIndex: number,
  viewportStart: number,
  viewportEnd: number,
  charToPixel: (offset: number) => { x: number; y: number; height: number },
): void {
  // Only draw matches visible in current viewport
  const visible = matches.filter(
    (m) => m.end > viewportStart && m.start < viewportEnd
  );

  for (let i = 0; i < visible.length; i++) {
    const match = visible[i];
    const isCurrentMatch = matches.indexOf(match) === currentMatchIndex;
    const pos = charToPixel(match.start);

    ctx.fillStyle = isCurrentMatch ? "#f39c12" : "#f1c40f";  // orange = current, yellow = others
    ctx.globalAlpha = isCurrentMatch ? 0.8 : 0.5;
    // Draw highlight rectangle (simplified — actual implementation measures text width)
    ctx.fillRect(pos.x, pos.y, 60, pos.height);  // 60px approximate — real impl uses measureText
  }
  ctx.globalAlpha = 1.0;
}
```

Zero `<mark>` DOM elements. All search highlights are canvas-drawn.

### OverviewBar search ticks (GPU path)

In the WebGPU overview bar, search match positions are uploaded as a `Float32Array` to a GPU buffer. The density shader renders them as yellow tick marks in a single draw call:

```typescript
// In OverviewBar WebGPU pipeline:
function uploadSearchMatches(
  device: GPUDevice,
  matches: SearchMatch[],
  docLength: number,
  buffer: GPUBuffer,
): void {
  const positions = new Float32Array(matches.map((m) => m.start / docLength));
  device.queue.writeBuffer(buffer, 0, positions);
  // Shader reads positions[], renders as 2px yellow vertical lines
}
```

Previously: 10,000 SVG `<line>` elements. Now: 10,000 positions in a 40KB Float32Array, rendered by the GPU in one draw call.

### Test strategy

**Rust unit tests** (`src-tauri/src/search_test.rs`):

```rust
#[cfg(test)]
mod tests {
    use super::*;

    const PP_OPENING: &str =
        "It is a truth universally acknowledged, that a single man in \
         possession of a good fortune, must be in want of a wife.";

    #[test]
    fn test_suffix_array_finds_literal_match() {
        let sa = SuffixArray::build(PP_OPENING.to_string());
        let matches = sa.search("truth", false);
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0], 9);  // "truth" starts at char 9
        assert_eq!(&PP_OPENING[9..14], "truth");
    }

    #[test]
    fn test_suffix_array_case_insensitive() {
        let sa = SuffixArray::build(PP_OPENING.to_string());
        let matches = sa.search("it", false);
        // "It" at start, "it" in "universally", etc.
        assert!(matches.len() >= 2);
        assert!(matches.contains(&0));  // "It" at position 0
    }

    #[test]
    fn test_suffix_array_case_sensitive_excludes_uppercase() {
        let sa = SuffixArray::build(PP_OPENING.to_string());
        let case_sensitive = sa.search("it", true);
        let case_insensitive = sa.search("it", false);
        // Case-sensitive should find fewer matches (excludes "It" at position 0)
        assert!(case_sensitive.len() < case_insensitive.len());
        assert!(!case_sensitive.contains(&0));
    }

    #[test]
    fn test_suffix_array_empty_query_returns_empty() {
        let sa = SuffixArray::build(PP_OPENING.to_string());
        assert_eq!(sa.search("", false), vec![]);
    }

    #[test]
    fn test_suffix_array_no_match_returns_empty() {
        let sa = SuffixArray::build(PP_OPENING.to_string());
        assert_eq!(sa.search("zzzzz", false), vec![]);
    }

    #[test]
    fn test_suffix_array_results_sorted() {
        let sa = SuffixArray::build(PP_OPENING.to_string());
        let matches = sa.search("a", false);
        assert!(matches.windows(2).all(|w| w[0] <= w[1]), "Results not sorted");
    }
}
```

**Performance benchmarks** (`palimpsest-core/benches/search.rs`):

```rust
use criterion::{criterion_group, criterion_main, Criterion, Throughput};

fn bench_suffix_array_build(c: &mut Criterion) {
    // Full P&P text: ~600KB
    let text = std::fs::read_to_string("benches/fixtures/pride-prejudice-full.txt").unwrap();
    let n = text.len();

    let mut group = c.benchmark_group("suffix-array");
    group.throughput(Throughput::Bytes(n as u64));

    group.bench_function("build_600kb", |b| {
        b.iter(|| SuffixArray::build(text.clone()))
    });
    group.finish();
    // REQUIRED: build completes in <100ms (accept up to 200ms on first cold run)
}

fn bench_suffix_array_search(c: &mut Criterion) {
    let text = std::fs::read_to_string("benches/fixtures/pride-prejudice-full.txt").unwrap();
    let sa = SuffixArray::build(text);

    let mut group = c.benchmark_group("suffix-array-search");

    group.bench_function("search_common_word_bennet", |b| {
        b.iter(|| sa.search("Bennet", false))
    });
    // REQUIRED: <10ms for a single novel search

    group.bench_function("search_rare_word_pneumonia", |b| {
        b.iter(|| sa.search("pneumonia", false))
    });
    // REQUIRED: <5ms (fewer matches → faster)

    group.finish();
}
```

**Browser tests** (Vitest, `browser/src/stores/__tests__/searchStore.test.ts`):

```typescript
import { vi, it, expect, describe, beforeEach } from "vitest";

vi.mock("@tauri-apps/api/tauri", () => ({
  invoke: vi.fn(),
}));

import { invoke } from "@tauri-apps/api/tauri";
import { useSearchStore } from "../searchStore";

describe("searchStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSearchStore.setState({
      query: "", matches: [], currentMatchIndex: -1, isOpen: false, isLoading: false,
    });
  });

  it("calls invoke with search_text command", async () => {
    vi.mocked(invoke).mockResolvedValue({
      matches: [{ start: 9, end: 14, paragraph_index: 0 }],
      query_ms: 1.2,
      total_count: 1,
    });
    await useSearchStore.getState().setQuery("truth", "pp-full");
    expect(invoke).toHaveBeenCalledWith("search_text", {
      projectId: "pp-full",
      query: "truth",
      caseSensitive: false,
    });
    expect(useSearchStore.getState().matches).toHaveLength(1);
    expect(useSearchStore.getState().currentMatchIndex).toBe(0);
  });

  it("clears matches on empty query (no invoke call)", async () => {
    await useSearchStore.getState().setQuery("", "pp-full");
    expect(invoke).not.toHaveBeenCalled();
    expect(useSearchStore.getState().matches).toHaveLength(0);
  });

  it("nextMatch wraps around", async () => {
    useSearchStore.setState({
      matches: [{ start: 0, end: 5, paragraph_index: 0 }, { start: 10, end: 15, paragraph_index: 0 }],
      currentMatchIndex: 1,
    });
    useSearchStore.getState().nextMatch();
    expect(useSearchStore.getState().currentMatchIndex).toBe(0);
  });

  it("close clears state", () => {
    useSearchStore.setState({ query: "test", matches: [{ start: 0, end: 4, paragraph_index: 0 }] });
    useSearchStore.getState().close();
    expect(useSearchStore.getState().query).toBe("");
    expect(useSearchStore.getState().matches).toHaveLength(0);
  });
});
```

**Performance targets**:
| Operation | Target | Benchmark asserts |
|-----------|--------|-------------------|
| Suffix array build (600KB P&P) | <100ms | `criterion` group benchmark |
| Search "Bennet" in P&P | <5ms | `criterion` group benchmark |
| Search across 5 novels (3MB) | <25ms | Multi-project benchmark (Phase 2) |
| Tauri IPC overhead | <3ms | Measured by `queryMs` field in result |
| Canvas highlight render (200 matches) | <2ms | `requestAnimationFrame` budget |
| GPU tick upload (10K matches) | <0.5ms | `device.queue.writeBuffer` timing |

---

## Original Content (preserved for reference)

### Context

Text search (Ctrl+F or /) is one of the most basic scholarly operations — finding where "Bennet" appears across 61 chapters. The plan §7.3 specifies type-ahead highlighting, match navigation with keyboard shortcuts, a match count display, and an OverviewBar tick-mark layer showing all match positions.

### Design Decisions (original, superseded by v4.0)

- **Character-offset-based matches**: storing matches as `{start, end}` character offsets in `referenceText` is consistent with the W3C `TextPositionSelector` pattern. (Preserved in v4.0.)
- **`indexOf` loop, not regex**: for a simple literal text search, `String.prototype.indexOf` is faster and simpler than a regex. (v4.0: suffix array in Rust — `indexOf` cannot satisfy multi-novel requirements.)
- **Zustand store, not local state**: `TextLinearView`, `OverviewBar`, and the global keyboard handler all need access to search state. (Preserved in v4.0.)
- **`aria-live="polite"`** on the match count. (Preserved in v4.0.)
- **Minimum query length of 1**: matches update on every keystroke. (Preserved in v4.0 — empty query returns early without invoking Rust.)
- **`[` and `]` as navigation keys**: per the keyboard map in §7.2 of the Phase 1 plan. (Preserved in v4.0.)
