use palimpsest_core::project::LoadedProject;
use std::path::Path;
use std::time::Instant;

fn main() {
    let project_dir = Path::new("/Users/nathanielcannon/Claude/Projects/palimpsest/core/data/pride-and-prejudice");
    
    let start = Instant::now();
    let project = LoadedProject::load(project_dir).expect("Failed to load project");
    let load_time = start.elapsed();
    
    println!("=== Pride & Prejudice — Real Data Performance ===");
    println!("Load time: {:?}", load_time);
    println!("Annotations: {}", project.total_annotations());
    println!("Memory: {} bytes ({:.1} KB)", 
        project.arena.memory_usage().total_bytes(),
        project.arena.memory_usage().total_bytes() as f64 / 1024.0);
    println!("Tracks: {:?}", project.arena.track_names());
    
    // Viewport query
    let start = Instant::now();
    let viewport = project.query_viewport(100_000, 107_000);
    let query_time = start.elapsed();
    println!("\nViewport query (100K-107K chars): {} annotations in {:?}", viewport.len(), query_time);
    
    // Density
    let start = Instant::now();
    let histograms = project.density_per_track(2000);
    let density_time = start.elapsed();
    println!("Per-track density (5 tracks × 2000 bins): {:?}", density_time);
    println!("Track histogram counts: {:?}", histograms.iter().map(|h| h.max_value() as u32).collect::<Vec<_>>());
}
