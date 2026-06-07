use crate::annotation::PackedAnnotation;

pub struct RangeIndex {
    sorted_by_start: Vec<u32>,
    sorted_by_end: Vec<u32>,
    annotations: *const [PackedAnnotation],
}

unsafe impl Send for RangeIndex {}
unsafe impl Sync for RangeIndex {}

impl RangeIndex {
    pub fn build(annotations: &[PackedAnnotation]) -> Self {
        let mut sorted_by_start: Vec<u32> = (0..annotations.len() as u32).collect();
        sorted_by_start.sort_unstable_by_key(|&i| annotations[i as usize].start);

        let mut sorted_by_end: Vec<u32> = (0..annotations.len() as u32).collect();
        sorted_by_end.sort_unstable_by_key(|&i| annotations[i as usize].end);

        Self {
            sorted_by_start,
            sorted_by_end,
            annotations: annotations as *const [PackedAnnotation],
        }
    }

    pub fn query(&self, range_start: u32, range_end: u32) -> Vec<u32> {
        let anns = unsafe { &*self.annotations };

        let start_bound = self
            .sorted_by_start
            .partition_point(|&i| anns[i as usize].start < range_end);

        let end_bound = self
            .sorted_by_end
            .partition_point(|&i| anns[i as usize].end <= range_start);

        let candidates_from_start: std::collections::HashSet<u32> =
            self.sorted_by_start[..start_bound].iter().copied().collect();

        let excluded: std::collections::HashSet<u32> =
            self.sorted_by_end[..end_bound].iter().copied().collect();

        candidates_from_start
            .difference(&excluded)
            .copied()
            .collect()
    }

    pub fn query_sorted(&self, range_start: u32, range_end: u32) -> Vec<u32> {
        let mut result = self.query(range_start, range_end);
        let anns = unsafe { &*self.annotations };
        result.sort_unstable_by_key(|&i| anns[i as usize].start);
        result
    }

    pub fn len(&self) -> usize {
        self.sorted_by_start.len()
    }

    pub fn is_empty(&self) -> bool {
        self.sorted_by_start.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::annotation::PackedAnnotation;

    fn make_ann(start: u32, end: u32) -> PackedAnnotation {
        PackedAnnotation {
            start,
            end,
            confidence: 8500,
            track_id: 0,
            evidence_level: 5,
            body_offset: 0,
        }
    }

    #[test]
    fn query_finds_overlapping() {
        let anns = vec![
            make_ann(0, 50),
            make_ann(40, 100),
            make_ann(100, 200),
            make_ann(150, 250),
            make_ann(300, 400),
        ];
        let index = RangeIndex::build(&anns);

        let result = index.query(45, 160);
        assert!(result.contains(&0)); // 0-50 overlaps 45-160
        assert!(result.contains(&1)); // 40-100 overlaps 45-160
        assert!(result.contains(&2)); // 100-200 overlaps 45-160
        assert!(result.contains(&3)); // 150-250 overlaps 45-160
        assert!(!result.contains(&4)); // 300-400 doesn't overlap
    }

    #[test]
    fn query_empty_range() {
        let anns = vec![make_ann(100, 200), make_ann(300, 400)];
        let index = RangeIndex::build(&anns);

        let result = index.query(200, 300);
        assert!(result.is_empty());
    }

    #[test]
    fn query_sorted_returns_ordered() {
        let anns = vec![
            make_ann(300, 400),
            make_ann(100, 200),
            make_ann(200, 350),
        ];
        let index = RangeIndex::build(&anns);

        let result = index.query_sorted(150, 350);
        assert_eq!(result.len(), 3);
        assert_eq!(result[0], 1); // start=100
        assert_eq!(result[1], 2); // start=200
        assert_eq!(result[2], 0); // start=300
    }

    #[test]
    fn large_index_performance() {
        let anns: Vec<_> = (0..20_000)
            .map(|i| make_ann(i * 50, i * 50 + 100))
            .collect();
        let index = RangeIndex::build(&anns);

        let result = index.query(500_000, 507_000);
        assert!(!result.is_empty());
        assert!(result.len() < 200);
    }
}
