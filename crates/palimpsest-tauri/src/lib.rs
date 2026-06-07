mod commands;
mod state;

use state::AppState;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState::new())
        .invoke_handler(tauri::generate_handler![
            commands::set_workspace,
            commands::load_project,
            commands::list_projects,
            commands::query_viewport,
            commands::update_filter,
            commands::get_density,
            commands::get_annotation_detail,
            commands::get_reference_text,
            commands::search_text,
            commands::get_project_info,
            commands::list_signals,
            commands::get_signal_data,
            commands::get_signal_manifest,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
