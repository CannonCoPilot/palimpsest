use criterion::{black_box, criterion_group, criterion_main, Criterion};
use palimpsest_core::annotation::PackedAnnotation;
use palimpsest_core::arena::AnnotationArena;
use palimpsest_core::density::DensityHistogram;
use palimpsest_core::filter::FilterEngine;
use palimpsest_core::range_index::RangeIndex;

fn create_large_dataset(n: usize) -> (AnnotationArena, Vec<PackedAnnotation>) {
    let mut arena = AnnotationArena::with_capacity(n, n * 20);
    let mut anns = Vec::with_capacity(n);

    for i in 0..n {
        let start = (i as u32) * 40;
        let end = start + 60 + (i as u32 % 40);
        let ann = PackedAnnotation {
            start,
            end,
            confidence: 5000 + (i as u16 % 5000),
            track_id: (i % 5) as u8,
            evidence_level: 3 + (i % 3) as u8,
            body_offset: arena.push_body(b"benchmark body data"),
        };
        arena.push(ann);
        anns.push(ann);
    }

    (arena, anns)
}

fn bench_filter_20k(c: &mut Criterion) {
    let (_arena, anns) = create_large_dataset(20_000);
    let mut engine = FilterEngine::new();
    engine.set_track_visible(2, false);
    engine.set_min_confidence(0.7);

    c.bench_function("filter_20k_annotations", |b| {
        b.iter(|| {
            let result = engine.filter_indices(black_box(&anns));
            black_box(result);
        })
    });
}

fn bench_range_query(c: &mut Criterion) {
    let (_arena, anns) = create_large_dataset(20_000);
    let index = RangeIndex::build(&anns);

    c.bench_function("range_query_20k_viewport_7000_chars", |b| {
        b.iter(|| {
            let result = index.query_sorted(black_box(400_000), black_box(407_000));
            black_box(result);
        })
    });
}

fn bench_density_histogram(c: &mut Criterion) {
    let (_arena, anns) = create_large_dataset(20_000);
    let filter = FilterEngine::new();
    let doc_length = 20_000 * 40 + 100;

    c.bench_function("density_2000_bins_20k_annotations", |b| {
        b.iter(|| {
            let hist = DensityHistogram::compute(
                black_box(&anns),
                &filter,
                doc_length,
                2000,
            );
            black_box(hist);
        })
    });
}

fn bench_density_per_track(c: &mut Criterion) {
    let (_arena, anns) = create_large_dataset(20_000);
    let filter = FilterEngine::new();
    let doc_length = 20_000 * 40 + 100;

    c.bench_function("density_per_track_5_tracks_2000_bins", |b| {
        b.iter(|| {
            let hists = DensityHistogram::compute_per_track(
                black_box(&anns),
                &filter,
                doc_length,
                2000,
                5,
            );
            black_box(hists);
        })
    });
}

fn bench_arena_memory(c: &mut Criterion) {
    c.bench_function("arena_push_20k_annotations", |b| {
        b.iter(|| {
            let mut arena = AnnotationArena::with_capacity(20_000, 400_000);
            for i in 0..20_000u32 {
                let body_offset = arena.push_body(b"body data here");
                arena.push(PackedAnnotation {
                    start: i * 40,
                    end: i * 40 + 60,
                    confidence: 8500,
                    track_id: (i % 5) as u8,
                    evidence_level: 5,
                    body_offset,
                });
            }
            black_box(arena.len());
        })
    });
}

criterion_group!(
    benches,
    bench_filter_20k,
    bench_range_query,
    bench_density_histogram,
    bench_density_per_track,
    bench_arena_memory,
);
criterion_main!(benches);
