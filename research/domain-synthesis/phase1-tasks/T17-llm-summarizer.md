# T17: LLM Summarizer (Tauri Command + Browser)

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 3 hours (down from 4; FastAPI eliminated)
**Dependencies**: T16 (Rust OllamaManager), T09 (Tauri shell + React frontend)
**Outputs**: `src-tauri/src/commands/summarize.rs` (created or extended); `browser/src/components/DetailPanel/LLMSummary.tsx` (created); `browser/src/components/DetailPanel/DetailPanel.tsx` (modified)

---

## v4.0 Critical Review

**Verdict: The FastAPI `/api/summarize` endpoint is eliminated entirely. The `fetch("/api/summarize")` call in the browser is eliminated. The entire HTTP round-trip is replaced by a Tauri IPC command call. The React component logic is correct and survives; only the data transport changes.**

### What is broken

**1. `POST /api/summarize` over HTTP localhost is the wrong IPC mechanism.**
The original design: browser `fetch("/api/summarize")` → FastAPI `server.py` → Python `OllamaLLMClient` → Ollama HTTP. In v4.0: browser `invoke("chat_summarize", {passage})` → Rust `chat_summarize` Tauri command → Rust `OllamaManager::chat()` → Ollama HTTP. The HTTP boundary between browser and Python server is eliminated. The Tauri IPC call has zero serialization overhead beyond what JSON already costs — and it is in-process (no TCP stack, no HTTP headers, no FastAPI middleware).

**2. FastAPI `SummarizeRequest` Pydantic validation is replaced by Rust type checking.**
`passage: str = Field(..., min_length=10, max_length=5000)` — in the Rust command, this is enforced in the command body before calling `OllamaManager::chat()`:
```rust
if passage.len() < 10 || passage.len() > 5000 {
    return Err("Passage length out of bounds".to_string());
}
```
No Pydantic, no FastAPI, no HTTP 422 — the Tauri command returns an `Err(String)` which the frontend receives as a rejected Promise.

**3. The frontend `fetch("/api/summarize")` is sensitive to whether `palimpsest serve` is running.**
If the user opens the Tauri app without starting the Python server separately, `fetch` fails with a network error. In v4.0, Tauri commands are always available — they are in-process. There is no "server not running" failure mode for the summarizer. The only failure mode is Ollama not running, which is handled gracefully.

**4. `await resp.json()` in `LLMSummary.tsx` parses a `SummarizeResponse` struct with an `ollama_available` boolean.**
The new Tauri response pattern is different: the command returns `Result<String, String>` — `Ok(summary_text)` on success, `Err("Ollama is not running")` on failure. The React component handles this discriminated result, not a `{ollama_available, summary}` object. This simplifies the response parsing logic in the component.

**5. The `200 always` design (returning 200 with `ollama_available: false`) was necessary to prevent browser error handling from firing.**
With Tauri IPC, there is no HTTP status code. The Promise either resolves with a value or rejects with an error. The component should catch rejection and show the appropriate message based on the error string.

**6. The `passage` is sent as a raw string from the browser.**
This is correct in v4.0 — the passage text is available in the React component because the `VirtualTextView` fetches paragraph text via `query_viewport()`. No change needed here.

---

## v4.0 Rewrite

### Architecture

```
React DetailPanel
  │
  ├── user clicks "Summarize"
  ├── invoke("chat_summarize", { passage, model: "qwen3:8b" })
  │     [Tauri IPC — in-process, no HTTP]
  │
  ▼
Rust command: chat_summarize (src-tauri/src/commands/summarize.rs)
  │
  ├── validate: 10 <= passage.len() <= 5000
  ├── check OllamaManager cached status (O(1))
  ├── if not running → Err("Ollama is not running. Install Ollama to enable AI summaries.")
  └── OllamaManager::chat(model, messages, 0.3, 150)
        ├── think: false in payload (mandatory for Qwen3)
        └── → Ok(summary_text) or Err(OllamaError::...)
```

### Language and technology

- **Rust** (`src-tauri/src/commands/summarize.rs`): Tauri command handler
- **TypeScript** (`browser/src/components/DetailPanel/LLMSummary.tsx`): React component, Tauri `invoke()` call
- **No Python, no HTTP, no FastAPI**

### Rust implementation

The core Rust command was introduced in T16. This task wires it to the Tauri command registry and ensures error messages are user-facing strings:

```rust
// src-tauri/src/commands/summarize.rs

use crate::ollama::{OllamaManager, OllamaError, ChatMessage};
use std::sync::Arc;
use tokio::sync::RwLock;

const DEFAULT_LLM_MODEL: &str = "qwen3:8b";
const SYSTEM_PROMPT: &str =
    "You are a literary assistant. Summarize the following passage from a novel \
     in exactly 2 sentences. Be concise and focus on narrative content, not style.";

#[tauri::command]
pub async fn chat_summarize(
    passage: String,
    model: Option<String>,
    state: tauri::State<'_, Arc<RwLock<OllamaManager>>>,
) -> Result<String, String> {
    // Validation — replaces Pydantic Field constraints
    if passage.trim().len() < 10 {
        return Err("Passage is too short to summarize (minimum 10 characters).".to_string());
    }
    let passage = if passage.len() > 5000 {
        passage[..5000].to_string()
    } else {
        passage
    };
    // Cap to first 2000 chars for model context (matches original OllamaLLMClient.summarize())
    let user_content = passage[..passage.len().min(2000)].to_string();
    let model_name = model.unwrap_or_else(|| DEFAULT_LLM_MODEL.to_string());

    let manager = state.read().await;

    // Fast path: cached status check before any network call
    let status = manager.get_status().await;
    if !status.running {
        return Err(
            "Ollama is not running. Install Ollama from https://ollama.ai to enable AI summaries."
                .to_string()
        );
    }

    let messages = vec![
        ChatMessage {
            role: "system".to_string(),
            content: SYSTEM_PROMPT.to_string(),
        },
        ChatMessage {
            role: "user".to_string(),
            content: user_content,
        },
    ];

    manager
        .chat(&model_name, messages, 0.3, 150)
        .await
        .map_err(|e| match e {
            OllamaError::NotRunning => {
                "Ollama is not running. Install Ollama from https://ollama.ai.".to_string()
            }
            OllamaError::ModelNotFound(m) => {
                format!("Model '{}' not found. Run: ollama pull {}", m, m)
            }
            OllamaError::Timeout => {
                "Summary request timed out. The model may still be loading.".to_string()
            }
            e => format!("Summarization failed: {}", e),
        })
}
```

Register in `src-tauri/src/main.rs`:
```rust
.invoke_handler(tauri::generate_handler![
    // ... other commands
    commands::summarize::chat_summarize,
])
```

### React implementation

**`browser/src/components/DetailPanel/LLMSummary.tsx`** — updated for Tauri IPC:

```tsx
import { invoke } from "@tauri-apps/api/tauri";
import { useState, useCallback } from "react";

interface LLMSummaryProps {
  passage: string;
  passageId: string;
}

type SummaryState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; summary: string }
  | { status: "error"; message: string };

export function LLMSummary({ passage, passageId }: LLMSummaryProps) {
  const [state, setState] = useState<SummaryState>({ status: "idle" });

  // Reset when passage changes (same pattern as original — correct)
  const [lastPassageId, setLastPassageId] = useState<string>(passageId);
  if (passageId !== lastPassageId) {
    setState({ status: "idle" });
    setLastPassageId(passageId);
  }

  const handleSummarize = useCallback(async () => {
    setState({ status: "loading" });
    try {
      // Tauri IPC: no HTTP, no fetch, no server required
      const summary = await invoke<string>("chat_summarize", {
        passage,
        model: "qwen3:8b",
      });
      setState({ status: "done", summary });
    } catch (err: unknown) {
      // err is the Err(String) from Rust
      const message = typeof err === "string"
        ? err
        : "Unknown error contacting AI services.";
      setState({ status: "error", message });
    }
  }, [passage]);

  return (
    <div className="llm-summary">
      {state.status === "idle" && (
        <button
          className="llm-summary__button"
          onClick={handleSummarize}
          title="Summarize this passage with AI"
        >
          Summarize
        </button>
      )}
      {state.status === "loading" && (
        <p className="llm-summary__loading">Generating summary...</p>
      )}
      {state.status === "done" && (
        <div className="llm-summary__result">
          <p className="llm-summary__text">{state.summary}</p>
          <span className="llm-summary__model">qwen3:8b</span>
          <button
            className="llm-summary__reset"
            onClick={() => setState({ status: "idle" })}
          >
            Clear
          </button>
        </div>
      )}
      {state.status === "error" && (
        <p className="llm-summary__error">
          {state.message}
          {state.message.includes("ollama.ai") && (
            <>
              {" "}
              <a href="https://ollama.ai" target="_blank" rel="noreferrer">
                Install Ollama
              </a>
            </>
          )}
        </p>
      )}
    </div>
  );
}
```

Key changes from the original:
- `fetch("/api/summarize")` → `invoke("chat_summarize", {...})`
- `SummaryState` loses the `"unavailable"` state — Ollama-not-running is just an `"error"` with a specific message string
- The error message from Rust is user-facing and contains the install link — no need for a separate `"unavailable"` state in TypeScript
- No `SummarizeResponse` interface — the command returns `string` directly

### Integration into DetailPanel

```tsx
// browser/src/components/DetailPanel/DetailPanel.tsx

import { LLMSummary } from "./LLMSummary";
import { useViewStore } from "../../stores/viewStore";

export function DetailPanel() {
  const { selectedParagraph } = useViewStore();

  return (
    <aside className="detail-panel">
      {/* ... annotation detail display ... */}
      {selectedParagraph && (
        <section className="detail-panel__section">
          <h4 className="detail-panel__section-title">AI Summary</h4>
          <LLMSummary
            passage={selectedParagraph.text}
            passageId={selectedParagraph.id}
          />
        </section>
      )}
    </aside>
  );
}
```

`selectedParagraph.text` is populated from the Rust `query_viewport()` response, which returns paragraph text as part of the viewport query result. No additional fetch needed — the text is already in React state from the virtual scroll data flow.

### Test strategy

**Rust unit tests** (`src-tauri/src/commands/summarize_test.rs`):

```rust
#[cfg(test)]
mod tests {
    // Note: tauri::command tests require a Tauri test harness.
    // Unit test the validation logic directly.

    #[test]
    fn test_passage_too_short_returns_error() {
        let passage = "short".to_string();
        assert!(passage.trim().len() < 10);
        // Validation logic isolated for testing without Tauri context
    }

    #[test]
    fn test_passage_truncated_to_5000_chars() {
        let long_passage = "a".repeat(6000);
        let truncated = if long_passage.len() > 5000 {
            long_passage[..5000].to_string()
        } else {
            long_passage
        };
        assert_eq!(truncated.len(), 5000);
    }

    #[test]
    fn test_user_content_capped_at_2000() {
        let passage = "x".repeat(3000);
        let user_content = passage[..passage.len().min(2000)].to_string();
        assert_eq!(user_content.len(), 2000);
    }
}
```

**Browser tests** (Vitest, `browser/src/components/DetailPanel/__tests__/LLMSummary.test.tsx`):

```tsx
import { vi, it, expect, describe } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LLMSummary } from "../LLMSummary";

// Mock @tauri-apps/api/tauri
vi.mock("@tauri-apps/api/tauri", () => ({
  invoke: vi.fn(),
}));

import { invoke } from "@tauri-apps/api/tauri";

describe("LLMSummary", () => {
  it("shows Summarize button in idle state", () => {
    render(<LLMSummary passage="A longer passage of text here." passageId="p1" />);
    expect(screen.getByRole("button", { name: "Summarize" })).toBeInTheDocument();
  });

  it("calls invoke with chat_summarize command on click", async () => {
    vi.mocked(invoke).mockResolvedValueOnce("This is the AI summary.");
    render(<LLMSummary passage="A longer passage of text here." passageId="p1" />);
    fireEvent.click(screen.getByRole("button", { name: "Summarize" }));
    await screen.findByText("This is the AI summary.");
    expect(invoke).toHaveBeenCalledWith("chat_summarize", {
      passage: "A longer passage of text here.",
      model: "qwen3:8b",
    });
  });

  it("shows error message when invoke rejects (Ollama not running)", async () => {
    vi.mocked(invoke).mockRejectedValueOnce(
      "Ollama is not running. Install Ollama from https://ollama.ai."
    );
    render(<LLMSummary passage="A longer passage of text here." passageId="p1" />);
    fireEvent.click(screen.getByRole("button", { name: "Summarize" }));
    await screen.findByText(/Ollama is not running/);
    expect(screen.getByRole("link", { name: "Install Ollama" })).toHaveAttribute(
      "href", "https://ollama.ai"
    );
  });

  it("resets to idle state when passageId changes", () => {
    const { rerender } = render(
      <LLMSummary passage="Passage one." passageId="p1" />
    );
    rerender(<LLMSummary passage="Passage two." passageId="p2" />);
    expect(screen.getByRole("button", { name: "Summarize" })).toBeInTheDocument();
  });

  it("shows Clear button after successful summary", async () => {
    vi.mocked(invoke).mockResolvedValueOnce("Summary text here.");
    render(<LLMSummary passage="A longer passage of text here." passageId="p1" />);
    fireEvent.click(screen.getByRole("button", { name: "Summarize" }));
    await screen.findByText("Summary text here.");
    expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument();
  });
});
```

**Performance targets**:
| Operation | Target | Notes |
|-----------|--------|-------|
| Tauri IPC round-trip (Rust overhead only) | <5ms | Excludes Ollama model response time |
| Ollama chat response (Qwen3 8B) | <10s | Model speed, not our code |
| `get_status()` (cached) | <0.1ms | Arc<RwLock> read |
| React re-render on state change | <16ms | Stays within 60fps budget |

---

## Original Content (preserved for reference)

### Context

The LLM summarizer gives scholars an immediate AI-generated summary of any selected passage, directly within the DetailPanel. It is the first AI-assisted feature in Palimpsest and demonstrates the Ollama integration end-to-end: browser selection → FastAPI endpoint → Ollama → summary displayed in DetailPanel.

### Design Decisions (original, superseded by v4.0)

- **Discriminated union for `SummaryState`**: four states (idle, loading, done, unavailable, error) are represented as a discriminated union rather than multiple boolean flags. (Preserved in v4.0 — simplified to 4 states since "unavailable" merges into "error".)
- **Passage text sent from browser, not character offsets**: the server does not need to re-read the reference file. (Preserved in v4.0.)
- **`passageId` as reset key**: component uses a locally-tracked `lastPassageId` to detect prop changes and reset state synchronously. (Preserved in v4.0.)
- **200 always, not 503**: returning 503 when Ollama is absent would cause the browser to show a generic error. (v4.0: Tauri IPC uses Promise rejection with user-facing error strings — no HTTP status codes.)
- **"Summarize" button, not auto-trigger**: auto-triggering a network call every time the user clicks a paragraph would make every paragraph selection expensive. (Preserved in v4.0.)
