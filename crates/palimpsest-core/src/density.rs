use crate::annotation::PackedAnnotation;
use crate::filter::FilterEngine;

pub struct DensityHistogram {
    pub bins: Vec<f32>,
    pub bin_width: u32,
    pub doc_length: u32,
    pub num_bins: usize,
}

impl DensityHistogram {
    pub fn compute(
        annotations: &[PackedAnnotation],
        filter: &FilterEngine,
        doc_length: u32,
        num_bins: usize,
    ) -> Self {
        let bin_width = (doc_length / num_bins as u32).max(1);
        let mut bins = vec![0.0f32; num_bins];

        for ann in annotations {
            if !filter.passes(ann) {
                continue;
            }
            let start_bin = (ann.start / bin_width) as usize;
            let end_bin = ((ann.end.saturating_sub(1)) / bin_width) as usize;

            let start_bin = start_bin.min(num_bins - 1);
            let end_bin = end_bin.min(num_bins - 1);

            for bin in start_bin..=end_bin {
                bins[bin] += 1.0;
            }
        }

        Self {
            bins,
            bin_width,
            doc_length,
            num_bins,
        }
    }

    pub fn compute_per_track(
        annotations: &[PackedAnnotation],
        filter: &FilterEngine,
        doc_length: u32,
        num_bins: usize,
        track_count: usize,
    ) -> Vec<DensityHistogram> {
        let bin_width = (doc_length / num_bins as u32).max(1);
        let mut all_bins = vec![vec![0.0f32; num_bins]; track_count];

        for ann in annotations {
            if !filter.passes(ann) {
                continue;
            }
            let track = ann.track_id as usize;
            if track >= track_count {
                continue;
            }
            let start_bin = (ann.start / bin_width).min(num_bins as u32 - 1) as usize;
            let end_bin = ((ann.end.saturating_sub(1)) / bin_width).min(num_bins as u32 - 1) as usize;

            for bin in start_bin..=end_bin {
                all_bins[track][bin] += 1.0;
            }
        }

        all_bins
            .into_iter()
            .map(|bins| DensityHistogram {
                bins,
                bin_width,
                doc_length,
                num_bins,
            })
            .collect()
    }

    pub fn max_value(&self) -> f32 {
        self.bins.iter().copied().fold(0.0f32, f32::max)
    }

    pub fn normalize(&mut self) {
        let max = self.max_value();
        if max > 0.0 {
            for bin in &mut self.bins {
                *bin /= max;
            }
        }
    }

    pub fn as_f32_slice(&self) -> &[f32] {
        &self.bins
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::annotation::PackedAnnotation;
    use crate::filter::FilterEngine;

    fn make_ann(start: u32, end: u32, track_id: u8) -> PackedAnnotation {
        PackedAnnotation {
            start,
            end,
            confidence: 8500,
            track_id,
            evidence_level: 5,
            body_offset: 0,
        }
    }

    #[test]
    fn basic_density() {
        let anns = vec![
            make_ann(0, 100, 0),
            make_ann(50, 150, 0),
            make_ann(900, 1000, 0),
        ];
        let filter = FilterEngine::new();
        let hist = DensityHistogram::compute(&anns, &filter, 1000, 10);

        assert_eq!(hist.bins[0], 2.0); // 0-100 contains 2 annotations
        assert_eq!(hist.bins[1], 1.0); // 100-200 contains 1 annotation
        assert_eq!(hist.bins[9], 1.0); // 900-1000 contains 1
        assert_eq!(hist.bins[5], 0.0); // 500-600 is empty
    }

    #[test]
    fn per_track_density() {
        let anns = vec![
            make_ann(0, 100, 0),
            make_ann(0, 100, 1),
            make_ann(500, 600, 0),
            make_ann(500, 600, 1),
            make_ann(500, 600, 1),
        ];
        let filter = FilterEngine::new();
        let hists = DensityHistogram::compute_per_track(&anns, &filter, 1000, 10, 2);

        assert_eq!(hists[0].bins[0], 1.0); // track 0, bin 0
        assert_eq!(hists[1].bins[0], 1.0); // track 1, bin 0
        assert_eq!(hists[0].bins[5], 1.0); // track 0, bin 5
        assert_eq!(hists[1].bins[5], 2.0); // track 1, bin 5 (two anns)
    }

    #[test]
    fn respects_filter() {
        let anns = vec![
            make_ann(0, 100, 0),
            make_ann(0, 100, 1),
        ];
        let mut filter = FilterEngine::new();
        filter.set_track_visible(1, false);

        let hist = DensityHistogram::compute(&anns, &filter, 1000, 10);
        assert_eq!(hist.bins[0], 1.0); // only track 0 counted
    }
}
