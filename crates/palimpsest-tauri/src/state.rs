use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Mutex;

use palimpsest_core::project::LoadedProject;

pub struct AppState {
    pub projects: Mutex<HashMap<String, LoadedProject>>,
    pub workspace: Mutex<Option<PathBuf>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            projects: Mutex::new(HashMap::new()),
            workspace: Mutex::new(None),
        }
    }
}
