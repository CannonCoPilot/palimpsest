use serde::Serialize;
use tauri::State;

use palimpsest_core::project::LoadedProject;

use crate::state::AppState;

#[derive(Serialize)]
pub struct ProjectInfo {
    id: String,
    title: String,
    author: Option<String>,
    year: Option<u32>,
    word_count: u32,
    paragraph_count: u32,
    sentence_count: u32,
    character_count: u32,
    total_annotations: usize,
    tracks: Vec<TrackInfo>,
}

#[derive(Serialize)]
pub struct TrackInfo {
    name: String,
    annotation_count: usize,
    track_id: u8,
}

#[derive(Serialize)]
pub struct ViewportAnnotation {
    index: u32,
    start: u32,
    end: u32,
    confidence: f32,
    track_id: u8,
    evidence_level: u8,
}

#[derive(Serialize)]
pub struct DensityData {
    bins: Vec<f32>,
    track_name: String,
    max_value: f32,
}

#[derive(Serialize)]
pub struct SearchResult {
    matches: Vec<SearchMatch>,
    total: usize,
}

#[derive(Serialize)]
pub struct SearchMatch {
    start: u32,
    end: u32,
    paragraph_index: u32,
}

#[tauri::command]
pub fn list_projects(state: State<AppState>) -> Result<Vec<ProjectListEntry>, String> {
    let workspace = state.workspace.lock().unwrap();
    let workspace_path = workspace.as_ref().ok_or("No workspace set")?;

    let mut entries = Vec::new();
    if let Ok(dir) = std::fs::read_dir(workspace_path) {
        for entry in dir.flatten() {
            let meta_path = entry.path().join("metadata.json");
            if meta_path.exists() {
                if let Ok(content) = std::fs::read_to_string(&meta_path) {
                    if let Ok(meta) = serde_json::from_str::<serde_json::Value>(&content) {
                        entries.push(ProjectListEntry {
                            id: meta["id"].as_str().unwrap_or("").to_string(),
                            title: meta["title"].as_str().unwrap_or("").to_string(),
                            author: meta["author"].as_str().map(|s| s.to_string()),
                            word_count: meta["word_count"].as_u64().unwrap_or(0) as u32,
                        });
                    }
                }
            }
        }
    }
    entries.sort_by(|a, b| a.title.cmp(&b.title));
    Ok(entries)
}

#[derive(Serialize)]
pub struct ProjectListEntry {
    id: String,
    title: String,
    author: Option<String>,
    word_count: u32,
}

#[tauri::command]
pub fn set_workspace(
    path: String,
    state: State<AppState>,
) -> Result<(), String> {
    let ws_path = std::path::PathBuf::from(&path);
    if !ws_path.is_dir() {
        return Err(format!("Workspace not found: {path}"));
    }
    *state.workspace.lock().unwrap() = Some(ws_path);
    Ok(())
}

#[tauri::command]
pub fn load_project(
    project_id: String,
    state: State<AppState>,
) -> Result<ProjectInfo, String> {
    let workspace = state.workspace.lock().unwrap();
    let workspace_path = workspace.as_ref().ok_or("No workspace set. Call set_workspace first.")?;
    let project_dir = workspace_path.join(&project_id);

    let project = LoadedProject::load(&project_dir)
        .map_err(|e| format!("Failed to load project: {e}"))?;

    let info = build_project_info(&project);

    let mut projects = state.projects.lock().unwrap();
    projects.insert(project_id, project);

    Ok(info)
}

#[tauri::command]
pub fn get_project_info(
    project_id: String,
    state: State<AppState>,
) -> Result<ProjectInfo, String> {
    let projects = state.projects.lock().unwrap();
    let project = projects.get(&project_id).ok_or("Project not loaded")?;
    Ok(build_project_info(project))
}

#[tauri::command]
pub fn query_viewport(
    project_id: String,
    start: u32,
    end: u32,
    state: State<AppState>,
) -> Result<Vec<ViewportAnnotation>, String> {
    let projects = state.projects.lock().unwrap();
    let project = projects.get(&project_id).ok_or("Project not loaded")?;

    let indices = project.query_viewport(start, end);
    let annotations: Vec<ViewportAnnotation> = indices
        .iter()
        .map(|&i| {
            let ann = project.arena.get(i);
            ViewportAnnotation {
                index: i,
                start: ann.start,
                end: ann.end,
                confidence: ann.confidence_f32(),
                track_id: ann.track_id,
                evidence_level: ann.evidence_level,
            }
        })
        .collect();

    Ok(annotations)
}

#[tauri::command]
pub fn update_filter(
    project_id: String,
    track_mask: u64,
    min_confidence: f32,
    state: State<AppState>,
) -> Result<usize, String> {
    let mut projects = state.projects.lock().unwrap();
    let project = projects.get_mut(&project_id).ok_or("Project not loaded")?;

    project.filter = palimpsest_core::filter::FilterEngine::new();
    for track_id in 0..64u8 {
        project.filter.set_track_visible(track_id, (track_mask >> track_id) & 1 == 1);
    }
    project.filter.set_min_confidence(min_confidence);

    Ok(project.visible_annotations())
}

#[tauri::command]
pub fn get_density(
    project_id: String,
    num_bins: usize,
    state: State<AppState>,
) -> Result<Vec<DensityData>, String> {
    let projects = state.projects.lock().unwrap();
    let project = projects.get(&project_id).ok_or("Project not loaded")?;

    let histograms = project.density_per_track(num_bins);
    let track_names = project.arena.track_names();

    let data: Vec<DensityData> = histograms
        .into_iter()
        .enumerate()
        .map(|(i, hist)| DensityData {
            max_value: hist.max_value(),
            bins: hist.bins,
            track_name: track_names.get(i).cloned().unwrap_or_default(),
        })
        .collect();

    Ok(data)
}

#[tauri::command]
pub fn get_annotation_detail(
    project_id: String,
    annotation_index: u32,
    state: State<AppState>,
) -> Result<String, String> {
    let projects = state.projects.lock().unwrap();
    let project = projects.get(&project_id).ok_or("Project not loaded")?;

    let json = project.annotation_json(annotation_index);
    Ok(json.to_string())
}

#[tauri::command]
pub fn search_text(
    project_id: String,
    query: String,
    case_sensitive: bool,
    state: State<AppState>,
) -> Result<SearchResult, String> {
    let projects = state.projects.lock().unwrap();
    let project = projects.get(&project_id).ok_or("Project not loaded")?;

    if query.len() < 2 {
        return Ok(SearchResult { matches: vec![], total: 0 });
    }

    let text = &project.reference_text;
    let search_text: String;
    let search_query: String;

    let (haystack, needle) = if case_sensitive {
        (text.as_str(), query.as_str())
    } else {
        search_text = text.to_lowercase();
        search_query = query.to_lowercase();
        (search_text.as_str(), search_query.as_str())
    };

    let mut matches = Vec::new();
    let mut pos = 0;
    let mut para_idx = 0u32;
    let para_breaks: Vec<usize> = text
        .match_indices("\n\n")
        .map(|(i, _)| i)
        .collect();

    while let Some(idx) = haystack[pos..].find(needle) {
        let abs_pos = pos + idx;
        while (para_idx as usize) < para_breaks.len()
            && para_breaks[para_idx as usize] < abs_pos
        {
            para_idx += 1;
        }
        matches.push(SearchMatch {
            start: abs_pos as u32,
            end: (abs_pos + needle.len()) as u32,
            paragraph_index: para_idx,
        });
        pos = abs_pos + 1;
    }

    let total = matches.len();
    Ok(SearchResult { matches, total })
}

#[tauri::command]
pub fn get_reference_text(
    project_id: String,
    state: State<AppState>,
) -> Result<String, String> {
    let projects = state.projects.lock().unwrap();
    let project = projects.get(&project_id).ok_or("Project not loaded")?;
    Ok(project.reference_text.clone())
}

#[derive(Serialize)]
pub struct SignalInfo {
    name: String,
    signal_type: String,
    dimensions: Vec<usize>,
}

#[tauri::command]
pub fn list_signals(
    project_id: String,
    state: State<AppState>,
) -> Result<Vec<SignalInfo>, String> {
    let workspace = state.workspace.lock().unwrap();
    let workspace_path = workspace.as_ref().ok_or("No workspace set")?;
    let signals_dir = workspace_path.join(&project_id).join("signals");

    let mut signals = Vec::new();
    if signals_dir.is_dir() {
        if let Ok(entries) = std::fs::read_dir(&signals_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().is_some_and(|e| e == "json") {
                    if let Ok(content) = std::fs::read_to_string(&path) {
                        if let Ok(manifest) = serde_json::from_str::<serde_json::Value>(&content) {
                            signals.push(SignalInfo {
                                name: manifest["name"]
                                    .as_str()
                                    .unwrap_or_default()
                                    .to_string(),
                                signal_type: manifest["type"]
                                    .as_str()
                                    .unwrap_or_default()
                                    .to_string(),
                                dimensions: manifest["dimensions"]
                                    .as_array()
                                    .map(|a| {
                                        a.iter()
                                            .filter_map(|v| v.as_u64().map(|n| n as usize))
                                            .collect()
                                    })
                                    .unwrap_or_default(),
                            });
                        }
                    }
                }
            }
        }
    }
    signals.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(signals)
}

#[tauri::command]
pub fn get_signal_data(
    project_id: String,
    signal_name: String,
    state: State<AppState>,
) -> Result<Vec<f32>, String> {
    let workspace = state.workspace.lock().unwrap();
    let workspace_path = workspace.as_ref().ok_or("No workspace set")?;
    let signals_dir = workspace_path.join(&project_id).join("signals");

    let signal = palimpsest_core::SignalData::load(&signals_dir, &signal_name)
        .map_err(|e| format!("Failed to load signal: {e}"))?;

    signal
        .as_f32_slice()
        .map(|s| s.to_vec())
        .ok_or_else(|| "Signal has no binary data".to_string())
}

#[tauri::command]
pub fn get_signal_manifest(
    project_id: String,
    signal_name: String,
    state: State<AppState>,
) -> Result<serde_json::Value, String> {
    let workspace = state.workspace.lock().unwrap();
    let workspace_path = workspace.as_ref().ok_or("No workspace set")?;
    let signals_dir = workspace_path.join(&project_id).join("signals");
    let manifest_path = signals_dir.join(format!("{signal_name}.json"));

    let content = std::fs::read_to_string(&manifest_path)
        .map_err(|e| format!("Failed to read manifest: {e}"))?;
    serde_json::from_str(&content).map_err(|e| format!("Invalid manifest JSON: {e}"))
}

fn build_project_info(project: &LoadedProject) -> ProjectInfo {
    let track_names = project.arena.track_names();
    let annotations = project.arena.annotations();

    let mut track_counts: Vec<usize> = vec![0; track_names.len()];
    for ann in annotations {
        if (ann.track_id as usize) < track_counts.len() {
            track_counts[ann.track_id as usize] += 1;
        }
    }

    let tracks: Vec<TrackInfo> = track_names
        .iter()
        .enumerate()
        .map(|(i, name)| TrackInfo {
            name: name.clone(),
            annotation_count: track_counts.get(i).copied().unwrap_or(0),
            track_id: i as u8,
        })
        .collect();

    ProjectInfo {
        id: project.metadata.id.clone(),
        title: project.metadata.title.clone(),
        author: project.metadata.author.clone(),
        year: project.metadata.year,
        word_count: project.metadata.word_count,
        paragraph_count: project.metadata.paragraph_count,
        sentence_count: project.metadata.sentence_count,
        character_count: project.metadata.character_count,
        total_annotations: project.total_annotations(),
        tracks,
    }
}
