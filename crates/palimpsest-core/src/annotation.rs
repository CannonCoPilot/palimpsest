use static_assertions::assert_eq_size;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(C)]
pub struct PackedAnnotation {
    pub start: u32,
    pub end: u32,
    pub confidence: u16,
    pub track_id: u8,
    pub evidence_level: u8,
    pub body_offset: u32,
}

assert_eq_size!(PackedAnnotation, [u8; 16]);

impl PackedAnnotation {
    #[inline]
    pub fn confidence_f32(&self) -> f32 {
        self.confidence as f32 / 10000.0
    }

    #[inline]
    pub fn overlaps(&self, range_start: u32, range_end: u32) -> bool {
        self.start < range_end && self.end > range_start
    }

    #[inline]
    pub fn length(&self) -> u32 {
        self.end - self.start
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum EvidenceLevel {
    E1 = 1,
    E2 = 2,
    E3 = 3,
    E4 = 4,
    E5 = 5,
}

impl EvidenceLevel {
    pub fn from_str(s: &str) -> Self {
        match s {
            "E1" => Self::E1,
            "E2" => Self::E2,
            "E3" => Self::E3,
            "E4" => Self::E4,
            _ => Self::E5,
        }
    }

    pub fn as_u8(self) -> u8 {
        self as u8
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn packed_annotation_is_16_bytes() {
        assert_eq!(std::mem::size_of::<PackedAnnotation>(), 16);
    }

    #[test]
    fn confidence_conversion() {
        let ann = PackedAnnotation {
            start: 0,
            end: 100,
            confidence: 8500,
            track_id: 0,
            evidence_level: 5,
            body_offset: 0,
        };
        assert!((ann.confidence_f32() - 0.85).abs() < 0.001);
    }

    #[test]
    fn overlap_detection() {
        let ann = PackedAnnotation {
            start: 100,
            end: 200,
            confidence: 9000,
            track_id: 0,
            evidence_level: 5,
            body_offset: 0,
        };
        assert!(ann.overlaps(150, 250));
        assert!(ann.overlaps(50, 150));
        assert!(!ann.overlaps(200, 300));
        assert!(!ann.overlaps(0, 100));
    }
}
