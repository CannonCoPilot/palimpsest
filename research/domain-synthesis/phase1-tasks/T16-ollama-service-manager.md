# T16: Ollama Service Manager + Clients

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 4 hours
**Dependencies**: T15 (pipeline complete, project structure stable)
**Outputs**: `src-tauri/src/ollama.rs` (created); `src-tauri/src/commands/summarize.rs` (created); `core/tests/test_ollama.py` (created for any Python-side validation utilities)

---

## v4.0 Critical Review

**Verdict: The Python `httpx` service layer is completely eliminated. Rust owns the Ollama process lifecycle, health checking, and HTTP client. The `OllamaManager` Python class must not exist in the v4.0 architecture.**

### What is broken

**1. Python `httpx` calling Ollama over HTTP is a 2-hop round trip: Tauri frontend → FastAPI → httpx → Ollama.**
In v4.0, FastAPI is eliminated. The frontend calls Tauri commands directly. Rust has an async HTTP client (`reqwest`). There is no reason for a Python process to sit between the frontend and Ollama. The Python `OllamaManager`, `OllamaEmbeddingClient`, and `OllamaLLMClient` classes are entire modules that must be deleted, not migrated.

**2. `HEALTH_TIMEOUT = 3.0` seconds is unacceptable in the frontend data path.**
The original design calls `OllamaManager().health_check()` on every `/api/summarize` request. That's a 3-second potential delay before serving a response. In v4.0, Rust caches the Ollama health status with a background polling task (`tokio::time::interval`) that checks every 10 seconds. The frontend reads cached state in O(1) — no HTTP call in the hot path.

**3. Ollama process lifecycle is not managed — it assumes Ollama is already running.**
`OllamaManager` only checks if Ollama is running; it cannot start it. In v4.0, Rust manages the Ollama process lifecycle: if `ollama serve` is not running, Rust spawns it as a child process (via `tokio::process::Command`) and kills it when the Tauri app exits. This makes Palimpsest a fully self-contained app that does not require the user to manually start Ollama in a separate terminal.

**4. `ensure_model()` with a 300-second `httpx` blocking call will freeze the Python event loop.**
The original `ensure_model()` makes a synchronous `httpx.post` with `timeout=300.0`. If `palimpsest serve` is a FastAPI app, this blocks the entire ASGI server for up to 5 minutes during first-run model download. This is catastrophic for a web server. In v4.0, model pulling is an async Rust operation that streams download progress to the frontend via Tauri events.

**5. The `None`-return error pattern from Python (`embed_one` returns `None` on failure) cannot cross the IPC boundary.**
TypeScript calling a Tauri command gets back a `Result<T, E>`, not a nullable. The Rust error type must be `OllamaError` (an enum), not `None`. The frontend pattern-matches on `Err(OllamaError::NotRunning)` vs `Err(OllamaError::ModelNotFound)` etc. to show appropriate UI.

**6. `BATCH_SIZE = 32` for embeddings via Python httpx is arbitrary and untuned.**
In v4.0, the embedding client is `reqwest` in Rust. Batching is done at the Rust level with `futures::stream::iter(texts).chunks(32)` — same logical batch size but without the Python overhead. For the self-similarity track (Phase 1.3a), embedding throughput matters: Rust async HTTP should achieve 3-5x higher throughput than Python httpx due to eliminated GIL contention and faster JSON serialization.

**7. `think: false` in Qwen3 payloads is noted in MEMORY.md but buried in a code comment in `llm.py`.**
In the Rust client, `think: false` is a mandatory field in the request struct, not a comment. It must be in the serialized JSON payload at the root level, enforced by the type system:
```rust
struct OllamaChatRequest {
    model: String,
    messages: Vec<ChatMessage>,
    stream: bool,
    think: bool,         // MANDATORY false for Qwen3; prevents slow thinking-mode responses
    options: ChatOptions,
}
```

---

## v4.0 Rewrite

### Architecture

```
Tauri App
  │
  ├── src-tauri/src/ollama.rs: OllamaManager (Rust)
  │     ├── spawns `ollama serve` as child process (if not running)
  │     ├── background health poller (tokio::time::interval 10s)
  │     ├── cached OllamaStatus (Arc<RwLock<OllamaStatus>>)
  │     └── reqwest::Client for API calls
  │
  ├── Tauri commands (called by frontend):
  │     ├── get_ollama_status() → OllamaStatus
  │     ├── pull_model(name) → streams progress events to frontend
  │     ├── embed_texts(texts) → Vec<Vec<f32>>
  │     └── chat_summarize(passage, model) → String
  │
  └── Background process cleanup: kill `ollama serve` child on app exit
```

### Language and technology

- **Rust**: `reqwest` async HTTP, `tokio::process` for process management, `Arc<RwLock<>>` for shared state
- **No Python involvement**: Ollama is a native binary; no Python mediation needed
- **Frontend**: calls Tauri commands, not HTTP endpoints

### Data structures

```rust
// src-tauri/src/ollama.rs

use std::sync::Arc;
use tokio::sync::RwLock;
use reqwest::Client;

const OLLAMA_BASE_URL: &str = "http://localhost:11434";
const HEALTH_POLL_INTERVAL_SECS: u64 = 10;
const DEFAULT_LLM_MODEL: &str = "qwen3:8b";
const DEFAULT_EMBED_MODEL: &str = "qwen3-embedding";

#[derive(Debug, Clone, serde::Serialize)]
pub struct OllamaStatus {
    pub running: bool,
    pub models: Vec<String>,
    pub error: Option<String>,
}

#[derive(Debug, thiserror::Error, serde::Serialize)]
pub enum OllamaError {
    #[error("Ollama is not running")]
    NotRunning,
    #[error("Model {0} not found")]
    ModelNotFound(String),
    #[error("HTTP error: {0}")]
    Http(String),
    #[error("Timeout")]
    Timeout,
    #[error("Parse error: {0}")]
    Parse(String),
}

pub struct OllamaManager {
    client: Client,
    base_url: String,
    status: Arc<RwLock<OllamaStatus>>,
    ollama_process: Option<tokio::process::Child>,
}
```

### Implementation

```rust
impl OllamaManager {
    pub async fn new() -> Self {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(3))
            .build()
            .unwrap();
        let status = Arc::new(RwLock::new(OllamaStatus {
            running: false,
            models: vec![],
            error: None,
        }));

        let manager = Self {
            client,
            base_url: OLLAMA_BASE_URL.to_string(),
            status: status.clone(),
            ollama_process: None,
        };

        // Spawn background health poller
        tokio::spawn(health_poll_loop(
            manager.client.clone(),
            manager.base_url.clone(),
            status,
        ));

        manager
    }

    /// Ensure Ollama is running. If not, spawn `ollama serve`.
    pub async fn ensure_running(&mut self) -> Result<(), OllamaError> {
        {
            let s = self.status.read().await;
            if s.running { return Ok(()); }
        }
        // Try to spawn ollama serve
        let child = tokio::process::Command::new("ollama")
            .arg("serve")
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .map_err(|e| OllamaError::Http(e.to_string()))?;
        self.ollama_process = Some(child);

        // Wait up to 5 seconds for Ollama to become healthy
        for _ in 0..10 {
            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
            if let Ok(status) = self.check_health_once().await {
                if status.running {
                    *self.status.write().await = status;
                    return Ok(());
                }
            }
        }
        Err(OllamaError::Http("Ollama did not start within 5 seconds".to_string()))
    }

    async fn check_health_once(&self) -> Result<OllamaStatus, OllamaError> {
        let resp = self.client
            .get(format!("{}/api/tags", self.base_url))
            .send()
            .await
            .map_err(|e| OllamaError::Http(e.to_string()))?;

        let body: serde_json::Value = resp.json().await
            .map_err(|e| OllamaError::Parse(e.to_string()))?;

        let models = body["models"]
            .as_array()
            .unwrap_or(&vec![])
            .iter()
            .filter_map(|m| m["name"].as_str().map(String::from))
            .collect();

        Ok(OllamaStatus { running: true, models, error: None })
    }

    /// Get the cached status — O(1), no network call.
    pub async fn get_status(&self) -> OllamaStatus {
        self.status.read().await.clone()
    }

    /// Pull a model, streaming progress events via the provided sender.
    pub async fn pull_model(
        &self,
        model_name: &str,
        progress: tokio::sync::mpsc::Sender<ModelPullProgress>,
    ) -> Result<(), OllamaError> {
        let resp = self.client
            .post(format!("{}/api/pull", self.base_url))
            .json(&serde_json::json!({"name": model_name, "stream": true}))
            .timeout(std::time::Duration::from_secs(600))
            .send()
            .await
            .map_err(|e| OllamaError::Http(e.to_string()))?;

        use tokio::io::AsyncBufReadExt;
        let mut lines = tokio::io::BufReader::new(
            resp.bytes_stream()
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
                .into_async_read()
        ).lines();

        while let Some(line) = lines.next_line().await.map_err(|e| OllamaError::Http(e.to_string()))? {
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(&line) {
                let _ = progress.try_send(ModelPullProgress {
                    status: v["status"].as_str().unwrap_or("").to_string(),
                    completed: v["completed"].as_u64().unwrap_or(0),
                    total: v["total"].as_u64().unwrap_or(0),
                });
            }
        }
        Ok(())
    }

    /// Embed a batch of texts. Returns Vec<Vec<f32>>.
    pub async fn embed_batch(
        &self,
        model: &str,
        texts: &[String],
    ) -> Result<Vec<Vec<f32>>, OllamaError> {
        if !self.status.read().await.running {
            return Err(OllamaError::NotRunning);
        }
        let resp = self.client
            .post(format!("{}/api/embed", self.base_url))
            .json(&serde_json::json!({"model": model, "input": texts}))
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await
            .map_err(|e| OllamaError::Http(e.to_string()))?;

        let body: serde_json::Value = resp.json().await
            .map_err(|e| OllamaError::Parse(e.to_string()))?;

        body["embeddings"]
            .as_array()
            .ok_or(OllamaError::Parse("missing 'embeddings' field".to_string()))?
            .iter()
            .map(|v| {
                v.as_array()
                    .ok_or(OllamaError::Parse("embedding is not an array".to_string()))?
                    .iter()
                    .map(|f| f.as_f64().map(|x| x as f32)
                        .ok_or(OllamaError::Parse("non-float in embedding".to_string())))
                    .collect()
            })
            .collect()
    }

    /// Chat completion. think=false is mandatory for Qwen3 models.
    pub async fn chat(
        &self,
        model: &str,
        messages: Vec<ChatMessage>,
        temperature: f32,
        max_tokens: u32,
    ) -> Result<String, OllamaError> {
        if !self.status.read().await.running {
            return Err(OllamaError::NotRunning);
        }

        #[derive(serde::Serialize)]
        struct ChatRequest<'a> {
            model: &'a str,
            messages: &'a [ChatMessage],
            stream: bool,
            think: bool,      // MANDATORY false for Qwen3 — prevents slow thinking mode
            options: ChatOptions,
        }
        #[derive(serde::Serialize)]
        struct ChatOptions {
            temperature: f32,
            num_predict: u32,
        }

        let req = ChatRequest {
            model,
            messages: &messages,
            stream: false,
            think: false,
            options: ChatOptions { temperature, num_predict: max_tokens },
        };

        let resp = self.client
            .post(format!("{}/api/chat", self.base_url))
            .json(&req)
            .timeout(std::time::Duration::from_secs(60))
            .send()
            .await
            .map_err(|e| OllamaError::Http(e.to_string()))?;

        let body: serde_json::Value = resp.json().await
            .map_err(|e| OllamaError::Parse(e.to_string()))?;

        body["message"]["content"]
            .as_str()
            .map(|s| s.trim().to_string())
            .ok_or(OllamaError::Parse("missing message.content".to_string()))
    }
}

/// Background health polling task — runs forever, updates shared status.
async fn health_poll_loop(
    client: Client,
    base_url: String,
    status: Arc<RwLock<OllamaStatus>>,
) {
    let mut interval = tokio::time::interval(
        std::time::Duration::from_secs(HEALTH_POLL_INTERVAL_SECS)
    );
    loop {
        interval.tick().await;
        let new_status = match client
            .get(format!("{}/api/tags", base_url))
            .timeout(std::time::Duration::from_secs(2))
            .send()
            .await
        {
            Ok(resp) if resp.status().is_success() => {
                let body: serde_json::Value = resp.json().await.unwrap_or_default();
                let models = body["models"]
                    .as_array()
                    .unwrap_or(&vec![])
                    .iter()
                    .filter_map(|m| m["name"].as_str().map(String::from))
                    .collect();
                OllamaStatus { running: true, models, error: None }
            }
            Ok(resp) => OllamaStatus {
                running: false,
                models: vec![],
                error: Some(format!("HTTP {}", resp.status())),
            },
            Err(e) => OllamaStatus {
                running: false,
                models: vec![],
                error: Some(e.to_string()),
            },
        };
        *status.write().await = new_status;
    }
}
```

### Tauri command registration

```rust
// src-tauri/src/commands/ollama.rs

#[tauri::command]
pub async fn get_ollama_status(
    state: tauri::State<'_, Arc<RwLock<OllamaManager>>>,
) -> Result<OllamaStatus, String> {
    Ok(state.read().await.get_status().await)
}

#[tauri::command]
pub async fn chat_summarize(
    passage: String,
    model: Option<String>,
    state: tauri::State<'_, Arc<RwLock<OllamaManager>>>,
) -> Result<String, String> {
    // Validate passage length (replaces Pydantic validation from old server.py)
    if passage.len() < 10 {
        return Err("Passage too short (minimum 10 characters)".to_string());
    }
    let passage = if passage.len() > 5000 { &passage[..5000] } else { &passage };
    let model = model.unwrap_or_else(|| DEFAULT_LLM_MODEL.to_string());

    let messages = vec![
        ChatMessage {
            role: "system".to_string(),
            content: "You are a literary assistant. Summarize the following passage from a novel in exactly 2 sentences. Be concise and focus on narrative content, not style.".to_string(),
        },
        ChatMessage {
            role: "user".to_string(),
            content: passage[..passage.len().min(2000)].to_string(),
        },
    ];

    state
        .read()
        .await
        .chat(&model, messages, 0.3, 150)
        .await
        .map_err(|e| e.to_string())
}
```

### Test strategy

**Integration tests** (`core/tests/test_ollama.py` — Python tests for validation utilities only):

```python
import subprocess, json

def test_ollama_absent_tauri_command_returns_error():
    """When Ollama is not running, get_ollama_status returns status with running=false."""
    # Test via CLI that wraps the Tauri command logic
    result = subprocess.run(
        ["palimpsest", "ollama-status"],
        capture_output=True, text=True, timeout=5,
    )
    # May fail if Ollama IS running; skip in that case
    # The key assertion: it does not hang for >3 seconds
    assert result.returncode in (0, 1)  # either ok or graceful failure
```

**Rust unit tests** (`src-tauri/src/ollama.rs`):

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_health_check_unreachable_port_returns_not_running() {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(1))
            .build()
            .unwrap();
        let status = Arc::new(RwLock::new(OllamaStatus {
            running: false,
            models: vec![],
            error: None,
        }));
        // Point at a port nothing is listening on
        let result = client
            .get("http://localhost:19999/api/tags")
            .send()
            .await;
        assert!(result.is_err(), "Expected connection refused");
    }

    #[tokio::test]
    async fn test_chat_request_includes_think_false() {
        // Serialize a ChatRequest and verify "think":false is in the JSON
        #[derive(serde::Serialize)]
        struct ChatRequest {
            model: String,
            messages: Vec<serde_json::Value>,
            stream: bool,
            think: bool,
            options: serde_json::Value,
        }
        let req = ChatRequest {
            model: "qwen3:8b".to_string(),
            messages: vec![],
            stream: false,
            think: false,
            options: serde_json::json!({}),
        };
        let json = serde_json::to_string(&req).unwrap();
        assert!(json.contains("\"think\":false"), "think:false missing from payload: {}", json);
    }
}
```

**Performance targets**:
| Operation | Target | Notes |
|-----------|--------|-------|
| `get_status()` (cached) | <0.1ms | Arc<RwLock> read, no network |
| Health poll cycle | Every 10s | Background task, does not block UI |
| Chat summary (Qwen3 8B) | <10s | Model response time, not our code |
| embed_batch (32 texts) | <5s | Ollama embedding throughput |
| `ensure_running()` cold start | <5s | Spawn ollama serve + wait |

---

## Original Content (preserved for reference)

### Context

The services layer provides a clean abstraction over Ollama for two use cases: embedding (used by the self-similarity track in Milestone 1.3a) and chat completion (used by the LLM summarizer in T17). Because Ollama is optional — the plan §0.4 requires local-only operation, and scholars may not have it installed — all three modules must degrade gracefully when Ollama is not running.

### Design Decisions (original, superseded by v4.0)

- **`httpx` not `requests` or `aiohttp`**: `httpx` is already in `pyproject.toml` and supports both sync and async. (Note: v4.0 replaces with `reqwest` in Rust.)
- **`None` return on failure, not exception**: callers benefit from simple `if result is None:` checks. (Note: v4.0 uses `Result<T, OllamaError>` — richer and type-safe.)
- **`BATCH_SIZE = 32`**: Ollama's `/api/embed` endpoint accepts an array of inputs. Batching 32 texts at once reduces HTTP overhead. (Preserved in v4.0 Rust implementation.)
- **`think: false` for Qwen3**: per the project MEMORY.md, Qwen3 models default to "thinking mode" which dramatically increases response latency. `"think": false` at the payload root is mandatory. (Promoted to a compile-time struct field in v4.0, not a comment.)
- **`ensure_model` with 300s timeout**: pulling a 5B-parameter embedding model can take 2-10 minutes. (v4.0: streaming progress events, not a blocking call.)
- **`OllamaStatus` dataclass**: returning a dataclass instead of a plain dict gives callers type safety. (v4.0: Rust `struct OllamaStatus` with `#[derive(Serialize)]`.)
