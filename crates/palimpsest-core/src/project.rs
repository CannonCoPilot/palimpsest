use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::arena::AnnotationArena;
use crate::density::DensityHistogram;
use crate::filter::FilterEngine;
use crate::jsonl;
use crate::range_index::RangeIndex;

#[derive(Debug, Deserialize)]
pub struct ProjectMetadata {
    pub id: String,
    pub title: String,
    #[serde(default)]
    pub author: Option<String>,
    #[serde(default)]
    pub year: Option<u32>,
    #[serde(default)]
    pub word_count: u32,
    #[serde(default)]
    pub paragraph_count: u32,
    #[serde(default)]
    pub sentence_count: u32,
    #[serde(default)]
    pub character_count: u32,
}

pub struct LoadedProject {
    pub path: PathBuf,
    pub metadata: ProjectMetadata,
    pub reference_text: String,
    pub arena: AnnotationArena,
    pub range_index: RangeIndex,
    pub filter: FilterEngine,
}

impl LoadedProject {
    pub fn load(project_dir: &Path) -> Result<Self, ProjectLoadError> {
        let metadata_path = project_dir.join("metadata.json");
        if !metadata_path.exists() {
            return Err(ProjectLoadError::NotFound(project_dir.to_path_buf()));
        }

        let metadata_str = std::fs::read_to_string(&metadata_path)?;
        let metadata: ProjectMetadata = serde_json::from_str(&metadata_str)?;

        let reference_path = project_dir.join("reference.txt");
        let reference_text = std::fs::read_to_string(&reference_path)?;

        let tracks_dir = project_dir.join("tracks");
        let mut arena = AnnotationArena::with_capacity(20_000, 512_000);
        jsonl::load_project_tracks(&tracks_dir, &mut arena)?;

        let range_index = RangeIndex::build(arena.annotations());
        let filter = FilterEngine::new();

        Ok(Self {
            path: project_dir.to_path_buf(),
            metadata,
            reference_text,
            arena,
            range_index,
            filter,
        })
    }

    pub fn query_viewport(&self, start: u32, end: u32) -> Vec<u32> {
        let indices = self.range_index.query_sorted(start, end);
        indices
            .into_iter()
            .filter(|&i| self.filter.passes(self.arena.get(i)))
            .collect()
    }

    pub fn density_histogram(&self, num_bins: usize) -> DensityHistogram {
        DensityHistogram::compute(
            self.arena.annotations(),
            &self.filter,
            self.metadata.character_count,
            num_bins,
        )
    }

    pub fn density_per_track(&self, num_bins: usize) -> Vec<DensityHistogram> {
        DensityHistogram::compute_per_track(
            self.arena.annotations(),
            &self.filter,
            self.metadata.character_count,
            num_bins,
            self.arena.track_count(),
        )
    }

    pub fn annotation_json(&self, index: u32) -> &str {
        let ann = self.arena.get(index);
        self.arena.body_str(ann.body_offset)
    }

    pub fn total_annotations(&self) -> usize {
        self.arena.len()
    }

    pub fn visible_annotations(&self) -> usize {
        self.filter.count_passing(self.arena.annotations())
    }
}

#[derive(Debug, thiserror::Error)]
pub enum ProjectLoadError {
    #[error("Project not found: {0}")]
    NotFound(PathBuf),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("Parse error: {0}")]
    Parse(#[from] jsonl::ParseError),
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn create_test_project(dir: &Path) {
        fs::create_dir_all(dir.join("tracks")).unwrap();

        let metadata = r#"{"id":"test","title":"Test","word_count":1000,"paragraph_count":10,"sentence_count":50,"character_count":5000}"#;
        fs::write(dir.join("metadata.json"), metadata).unwrap();
        fs::write(dir.join("reference.txt"), "Hello world. ".repeat(100)).unwrap();

        let mut jsonl = String::new();
        for i in 0..100 {
            jsonl.push_str(&format!(
                r#"{{"body":{{"type":"test"}},"target":{{"selector":{{"start":{},"end":{}}}}},"palimpsest:confidence":0.85,"palimpsest:evidenceLevel":"E5"}}"#,
                i * 50, i * 50 + 30
            ));
            jsonl.push('\n');
        }
        fs::write(dir.join("tracks/entities.jsonl"), &jsonl).unwrap();
    }

    #[test]
    fn load_test_project() {
        let tmp = tempfile::tempdir().unwrap();
        let project_dir = tmp.path().join("test-project");
        create_test_project(&project_dir);

        let project = LoadedProject::load(&project_dir).unwrap();
        assert_eq!(project.metadata.title, "Test");
        assert_eq!(project.arena.len(), 100);
        assert_eq!(project.total_annotations(), 100);
    }

    #[test]
    fn query_viewport_respects_filter() {
        let tmp = tempfile::tempdir().unwrap();
        let project_dir = tmp.path().join("test-project");
        create_test_project(&project_dir);

        let mut project = LoadedProject::load(&project_dir).unwrap();

        let all = project.query_viewport(0, 5000);
        assert_eq!(all.len(), 100);

        let track_id = project.arena.track_id("entities").unwrap();
        project.filter.set_track_visible(track_id, false);

        let filtered = project.query_viewport(0, 5000);
        assert_eq!(filtered.len(), 0);
    }
}
