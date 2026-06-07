use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct SignalManifest {
    #[serde(rename = "type")]
    pub signal_type: String,
    pub name: String,
    pub source: String,
    #[serde(default)]
    pub reference_sha256: String,
    pub dimensions: Vec<usize>,
    #[serde(default = "default_dtype")]
    pub dtype: String,
    #[serde(default = "default_byte_order")]
    pub byte_order: String,
    #[serde(default)]
    pub data_file: String,
    #[serde(default)]
    pub segment_offsets: Vec<[u32; 2]>,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

fn default_dtype() -> String {
    "float32".to_string()
}

fn default_byte_order() -> String {
    "little-endian".to_string()
}

pub struct SignalData {
    pub manifest: SignalManifest,
    mmap: Option<memmap2::Mmap>,
}

impl SignalData {
    pub fn load(signals_dir: &Path, name: &str) -> Result<Self, SignalLoadError> {
        let manifest_path = signals_dir.join(format!("{name}.json"));
        let manifest_str =
            std::fs::read_to_string(&manifest_path).map_err(SignalLoadError::Io)?;
        let manifest: SignalManifest =
            serde_json::from_str(&manifest_str).map_err(SignalLoadError::Json)?;

        let mmap = if !manifest.data_file.is_empty() {
            let data_path = signals_dir.join(&manifest.data_file);
            let file = std::fs::File::open(&data_path).map_err(SignalLoadError::Io)?;
            let mmap = unsafe { memmap2::Mmap::map(&file).map_err(SignalLoadError::Io)? };
            Some(mmap)
        } else {
            None
        };

        Ok(Self { manifest, mmap })
    }

    pub fn as_f32_slice(&self) -> Option<&[f32]> {
        self.mmap.as_ref().map(|m| {
            let ptr = m.as_ptr() as *const f32;
            let len = m.len() / 4;
            unsafe { std::slice::from_raw_parts(ptr, len) }
        })
    }

    pub fn dimensions(&self) -> &[usize] {
        &self.manifest.dimensions
    }

    pub fn matrix_n(&self) -> Option<usize> {
        if self.manifest.signal_type == "matrix" && self.manifest.dimensions.len() == 2 {
            Some(self.manifest.dimensions[0])
        } else {
            None
        }
    }
}

#[derive(Debug, thiserror::Error)]
pub enum SignalLoadError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn load_signal_from_manifest_and_binary() {
        let tmp = tempfile::tempdir().unwrap();
        let signals_dir = tmp.path();

        // Write a 3x3 matrix
        let data: Vec<f32> = vec![1.0, 0.5, 0.3, 0.5, 1.0, 0.7, 0.3, 0.7, 1.0];
        let bytes: Vec<u8> = data.iter().flat_map(|f| f.to_le_bytes()).collect();
        fs::write(signals_dir.join("test.bin"), &bytes).unwrap();

        let manifest = r#"{
            "type": "matrix",
            "name": "test",
            "source": "test/0.1",
            "dimensions": [3, 3],
            "data_file": "test.bin"
        }"#;
        fs::write(signals_dir.join("test.json"), manifest).unwrap();

        let signal = SignalData::load(signals_dir, "test").unwrap();
        assert_eq!(signal.matrix_n(), Some(3));
        let slice = signal.as_f32_slice().unwrap();
        assert_eq!(slice.len(), 9);
        assert!((slice[0] - 1.0).abs() < 1e-6);
        assert!((slice[4] - 1.0).abs() < 1e-6);
    }

    #[test]
    fn sequence_signal_has_no_binary() {
        let tmp = tempfile::tempdir().unwrap();
        let manifest = r#"{
            "type": "sequence",
            "name": "alphabet",
            "source": "kmeans/0.1",
            "dimensions": [10],
            "metadata": {"sequence": "ABCDEFGHIJ"}
        }"#;
        fs::write(tmp.path().join("alphabet.json"), manifest).unwrap();

        let signal = SignalData::load(tmp.path(), "alphabet").unwrap();
        assert!(signal.as_f32_slice().is_none());
        assert_eq!(signal.manifest.signal_type, "sequence");
    }
}
