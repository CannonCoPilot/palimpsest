use crate::annotation::PackedAnnotation;

pub struct AnnotationArena {
    annotations: Vec<PackedAnnotation>,
    body_data: Vec<u8>,
    track_names: Vec<String>,
}

impl AnnotationArena {
    pub fn new() -> Self {
        Self {
            annotations: Vec::new(),
            body_data: Vec::new(),
            track_names: Vec::new(),
        }
    }

    pub fn with_capacity(annotation_count: usize, body_bytes: usize) -> Self {
        Self {
            annotations: Vec::with_capacity(annotation_count),
            body_data: Vec::with_capacity(body_bytes),
            track_names: Vec::new(),
        }
    }

    pub fn register_track(&mut self, name: &str) -> u8 {
        if let Some(idx) = self.track_names.iter().position(|n| n == name) {
            return idx as u8;
        }
        let idx = self.track_names.len() as u8;
        self.track_names.push(name.to_string());
        idx
    }

    pub fn track_id(&self, name: &str) -> Option<u8> {
        self.track_names.iter().position(|n| n == name).map(|i| i as u8)
    }

    pub fn track_name(&self, id: u8) -> Option<&str> {
        self.track_names.get(id as usize).map(|s| s.as_str())
    }

    pub fn push(&mut self, ann: PackedAnnotation) -> u32 {
        let idx = self.annotations.len() as u32;
        self.annotations.push(ann);
        idx
    }

    pub fn push_body(&mut self, data: &[u8]) -> u32 {
        let offset = self.body_data.len() as u32;
        self.body_data.extend_from_slice(data);
        self.body_data.push(0);
        offset
    }

    #[inline]
    pub fn get(&self, index: u32) -> &PackedAnnotation {
        &self.annotations[index as usize]
    }

    #[inline]
    pub fn annotations(&self) -> &[PackedAnnotation] {
        &self.annotations
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.annotations.len()
    }

    #[inline]
    pub fn is_empty(&self) -> bool {
        self.annotations.is_empty()
    }

    pub fn body_str(&self, offset: u32) -> &str {
        let start = offset as usize;
        let end = self.body_data[start..]
            .iter()
            .position(|&b| b == 0)
            .map(|p| start + p)
            .unwrap_or(self.body_data.len());
        std::str::from_utf8(&self.body_data[start..end]).unwrap_or("")
    }

    pub fn track_count(&self) -> usize {
        self.track_names.len()
    }

    pub fn track_names(&self) -> &[String] {
        &self.track_names
    }

    pub fn memory_usage(&self) -> ArenaMemoryStats {
        ArenaMemoryStats {
            annotation_bytes: self.annotations.len() * 16,
            body_bytes: self.body_data.len(),
            total_annotations: self.annotations.len(),
            total_tracks: self.track_names.len(),
        }
    }
}

impl Default for AnnotationArena {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug)]
pub struct ArenaMemoryStats {
    pub annotation_bytes: usize,
    pub body_bytes: usize,
    pub total_annotations: usize,
    pub total_tracks: usize,
}

impl ArenaMemoryStats {
    pub fn total_bytes(&self) -> usize {
        self.annotation_bytes + self.body_bytes
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::annotation::PackedAnnotation;

    #[test]
    fn arena_push_and_retrieve() {
        let mut arena = AnnotationArena::new();
        let track_id = arena.register_track("entities");
        let body_offset = arena.push_body(b"Mr. Bennet");

        let ann = PackedAnnotation {
            start: 100,
            end: 110,
            confidence: 8500,
            track_id,
            evidence_level: 4,
            body_offset,
        };
        let idx = arena.push(ann);

        assert_eq!(arena.len(), 1);
        assert_eq!(arena.get(idx).start, 100);
        assert_eq!(arena.body_str(body_offset), "Mr. Bennet");
    }

    #[test]
    fn track_registration() {
        let mut arena = AnnotationArena::new();
        let e = arena.register_track("entities");
        let s = arena.register_track("sentiment");
        let e2 = arena.register_track("entities");

        assert_eq!(e, 0);
        assert_eq!(s, 1);
        assert_eq!(e2, 0); // re-registration returns same ID
        assert_eq!(arena.track_name(0), Some("entities"));
        assert_eq!(arena.track_name(1), Some("sentiment"));
    }

    #[test]
    fn memory_stats() {
        let mut arena = AnnotationArena::with_capacity(1000, 8000);
        for i in 0..1000 {
            arena.push(PackedAnnotation {
                start: i * 100,
                end: i * 100 + 50,
                confidence: 8000,
                track_id: 0,
                evidence_level: 5,
                body_offset: 0,
            });
        }
        let stats = arena.memory_usage();
        assert_eq!(stats.total_annotations, 1000);
        assert_eq!(stats.annotation_bytes, 16000);
    }
}
