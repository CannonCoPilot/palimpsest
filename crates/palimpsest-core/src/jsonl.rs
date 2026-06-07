use std::io::{BufRead, BufReader, Read};
use std::path::Path;

use serde::Deserialize;

use crate::annotation::{EvidenceLevel, PackedAnnotation};
use crate::arena::AnnotationArena;

#[derive(Debug, thiserror::Error)]
pub enum ParseError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON parse error on line {line}: {source}")]
    Json {
        line: usize,
        source: serde_json::Error,
    },
    #[error("Missing selector start/end on line {0}")]
    MissingSelector(usize),
}

#[derive(Deserialize)]
struct MinimalAnnotation {
    #[allow(dead_code)]
    body: MinimalBody,
    target: MinimalTarget,
    #[serde(rename = "palimpsest:confidence", default)]
    confidence: Option<f64>,
    #[serde(rename = "palimpsest:evidenceLevel", default)]
    evidence_level: Option<String>,
}

#[derive(Deserialize)]
#[allow(dead_code)]
struct MinimalBody {
    #[serde(rename = "type", default)]
    body_type: Option<String>,
    #[serde(default)]
    value: Option<String>,
}

#[derive(Deserialize)]
struct MinimalTarget {
    selector: MinimalSelector,
}

#[derive(Deserialize)]
struct MinimalSelector {
    start: Option<u32>,
    end: Option<u32>,
}

pub fn load_jsonl_file(
    path: &Path,
    track_name: &str,
    arena: &mut AnnotationArena,
) -> Result<usize, ParseError> {
    let file = std::fs::File::open(path)?;
    let reader = BufReader::with_capacity(64 * 1024, file);
    load_jsonl_reader(reader, track_name, arena)
}

pub fn load_jsonl_reader<R: Read>(
    reader: BufReader<R>,
    track_name: &str,
    arena: &mut AnnotationArena,
) -> Result<usize, ParseError> {
    let track_id = arena.register_track(track_name);
    let mut count = 0;

    for (line_num, line_result) in reader.lines().enumerate() {
        let line = line_result?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let ann: MinimalAnnotation = serde_json::from_str(trimmed).map_err(|e| {
            ParseError::Json {
                line: line_num + 1,
                source: e,
            }
        })?;

        let start = ann
            .target
            .selector
            .start
            .ok_or(ParseError::MissingSelector(line_num + 1))?;
        let end = ann
            .target
            .selector
            .end
            .ok_or(ParseError::MissingSelector(line_num + 1))?;

        let confidence = ann.confidence.unwrap_or(0.85);
        let confidence_u16 = (confidence * 10000.0).round() as u16;

        let evidence = ann
            .evidence_level
            .as_deref()
            .map(EvidenceLevel::from_str)
            .unwrap_or(EvidenceLevel::E5);

        let body_json = trimmed.as_bytes();
        let body_offset = arena.push_body(body_json);

        let packed = PackedAnnotation {
            start,
            end,
            confidence: confidence_u16,
            track_id,
            evidence_level: evidence.as_u8(),
            body_offset,
        };

        arena.push(packed);
        count += 1;
    }

    Ok(count)
}

pub fn load_project_tracks(
    tracks_dir: &Path,
    arena: &mut AnnotationArena,
) -> Result<usize, ParseError> {
    let mut total = 0;

    if !tracks_dir.is_dir() {
        return Ok(0);
    }

    let mut entries: Vec<_> = std::fs::read_dir(tracks_dir)?
        .filter_map(|e| e.ok())
        .filter(|e| {
            e.path()
                .extension()
                .map(|ext| ext == "jsonl")
                .unwrap_or(false)
        })
        .collect();
    entries.sort_by_key(|e| e.file_name());

    for entry in entries {
        let path = entry.path();
        let track_name = path.file_stem().unwrap().to_string_lossy();
        let count = load_jsonl_file(&path, &track_name, arena)?;
        total += count;
    }

    Ok(total)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    const SAMPLE_JSONL: &str = r#"{"@context":"http://www.w3.org/ns/anno.jsonld","type":"Annotation","id":"urn:palimpsest:test:entities:1","body":{"type":"palimpsest:EntityAnnotation","value":"Mr. Bennet"},"target":{"source":"urn:palimpsest:test","selector":{"type":"TextPositionSelector","start":100,"end":110}},"creator":{"name":"spacy/en_core_web_lg"},"palimpsest:confidence":0.92,"palimpsest:evidenceLevel":"E4"}
{"@context":"http://www.w3.org/ns/anno.jsonld","type":"Annotation","id":"urn:palimpsest:test:entities:2","body":{"type":"palimpsest:EntityAnnotation","value":"Mrs. Bennet"},"target":{"source":"urn:palimpsest:test","selector":{"type":"TextPositionSelector","start":200,"end":211}},"creator":{"name":"spacy/en_core_web_lg"},"palimpsest:confidence":0.88,"palimpsest:evidenceLevel":"E4"}
"#;

    #[test]
    fn parse_w3c_jsonl() {
        let mut arena = AnnotationArena::new();
        let cursor = Cursor::new(SAMPLE_JSONL.as_bytes());
        let reader = BufReader::new(cursor);

        let count = load_jsonl_reader(reader, "entities", &mut arena).unwrap();

        assert_eq!(count, 2);
        assert_eq!(arena.len(), 2);

        let ann0 = arena.get(0);
        assert_eq!(ann0.start, 100);
        assert_eq!(ann0.end, 110);
        assert_eq!(ann0.confidence, 9200);
        assert_eq!(ann0.evidence_level, 4);

        let ann1 = arena.get(1);
        assert_eq!(ann1.start, 200);
        assert_eq!(ann1.end, 211);
        assert_eq!(ann1.confidence, 8800);
    }

    #[test]
    fn empty_lines_skipped() {
        let input = "\n\n{\"body\":{\"type\":\"test\"},\"target\":{\"selector\":{\"start\":0,\"end\":10}}}\n\n";
        let mut arena = AnnotationArena::new();
        let reader = BufReader::new(Cursor::new(input.as_bytes()));
        let count = load_jsonl_reader(reader, "test", &mut arena).unwrap();
        assert_eq!(count, 1);
    }
}
