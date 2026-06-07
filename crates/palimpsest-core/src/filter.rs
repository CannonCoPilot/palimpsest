use crate::annotation::PackedAnnotation;

pub struct FilterEngine {
    track_mask: u64,
    min_confidence: u16,
}

impl FilterEngine {
    pub fn new() -> Self {
        Self {
            track_mask: u64::MAX,
            min_confidence: 0,
        }
    }

    pub fn set_track_visible(&mut self, track_id: u8, visible: bool) {
        if visible {
            self.track_mask |= 1u64 << track_id;
        } else {
            self.track_mask &= !(1u64 << track_id);
        }
    }

    pub fn set_all_tracks_visible(&mut self, visible: bool) {
        self.track_mask = if visible { u64::MAX } else { 0 };
    }

    pub fn is_track_visible(&self, track_id: u8) -> bool {
        (self.track_mask >> track_id) & 1 == 1
    }

    pub fn set_min_confidence(&mut self, confidence: f32) {
        self.min_confidence = (confidence * 10000.0) as u16;
    }

    pub fn track_mask(&self) -> u64 {
        self.track_mask
    }

    #[inline]
    pub fn passes(&self, ann: &PackedAnnotation) -> bool {
        let track_visible = (self.track_mask >> ann.track_id) & 1 == 1;
        let confidence_ok = ann.confidence >= self.min_confidence;
        track_visible & confidence_ok
    }

    pub fn filter_indices(&self, annotations: &[PackedAnnotation]) -> Vec<u32> {
        annotations
            .iter()
            .enumerate()
            .filter(|(_, ann)| self.passes(ann))
            .map(|(i, _)| i as u32)
            .collect()
    }

    pub fn filter_range(
        &self,
        annotations: &[PackedAnnotation],
        range_start: u32,
        range_end: u32,
    ) -> Vec<u32> {
        annotations
            .iter()
            .enumerate()
            .filter(|(_, ann)| {
                self.passes(ann) && ann.overlaps(range_start, range_end)
            })
            .map(|(i, _)| i as u32)
            .collect()
    }

    pub fn count_passing(&self, annotations: &[PackedAnnotation]) -> usize {
        annotations.iter().filter(|ann| self.passes(ann)).count()
    }
}

impl Default for FilterEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::annotation::PackedAnnotation;

    fn make_ann(track_id: u8, confidence: u16, start: u32, end: u32) -> PackedAnnotation {
        PackedAnnotation {
            start,
            end,
            confidence,
            track_id,
            evidence_level: 5,
            body_offset: 0,
        }
    }

    #[test]
    fn filter_by_track() {
        let anns = vec![
            make_ann(0, 8500, 0, 100),
            make_ann(1, 8500, 100, 200),
            make_ann(0, 8500, 200, 300),
            make_ann(2, 8500, 300, 400),
        ];
        let mut engine = FilterEngine::new();
        engine.set_track_visible(1, false);

        let result = engine.filter_indices(&anns);
        assert_eq!(result, vec![0, 2, 3]);
    }

    #[test]
    fn filter_by_confidence() {
        let anns = vec![
            make_ann(0, 9000, 0, 100),
            make_ann(0, 5000, 100, 200),
            make_ann(0, 7500, 200, 300),
            make_ann(0, 8500, 300, 400),
        ];
        let mut engine = FilterEngine::new();
        engine.set_min_confidence(0.8);

        let result = engine.filter_indices(&anns);
        assert_eq!(result, vec![0, 3]);
    }

    #[test]
    fn filter_range() {
        let anns = vec![
            make_ann(0, 8500, 0, 100),
            make_ann(0, 8500, 50, 150),
            make_ann(0, 8500, 200, 300),
            make_ann(1, 8500, 250, 350),
        ];
        let mut engine = FilterEngine::new();
        engine.set_track_visible(1, false);

        // ann[0]: 0-100 overlaps 60-250? yes (0<250 && 100>60), track 0 visible
        // ann[1]: 50-150 overlaps 60-250? yes, track 0 visible
        // ann[2]: 200-300 overlaps 60-250? yes (200<250 && 300>60), track 0 visible
        // ann[3]: 250-350 overlaps 60-250? no (250 is NOT < 250), track 1 hidden anyway
        let result = engine.filter_range(&anns, 60, 250);
        assert_eq!(result, vec![0, 1, 2]);
    }

    #[test]
    fn toggle_all_tracks() {
        let anns = vec![
            make_ann(0, 8500, 0, 100),
            make_ann(1, 8500, 100, 200),
        ];
        let mut engine = FilterEngine::new();
        engine.set_all_tracks_visible(false);
        assert_eq!(engine.count_passing(&anns), 0);

        engine.set_all_tracks_visible(true);
        assert_eq!(engine.count_passing(&anns), 2);
    }

    #[test]
    fn performance_20k_annotations() {
        let anns: Vec<_> = (0..20_000)
            .map(|i| make_ann(i as u8 % 5, 5000 + (i as u16 % 5000), i * 40, i * 40 + 80))
            .collect();
        let mut engine = FilterEngine::new();
        engine.set_track_visible(2, false);
        engine.set_min_confidence(0.7);

        let result = engine.filter_indices(&anns);
        assert!(!result.is_empty());
        assert!(result.len() < 20_000);
    }
}
