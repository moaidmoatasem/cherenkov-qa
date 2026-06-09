#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod hardware;
mod settings;
mod wizard;

use tauri::Manager;

// ── Tauri commands ────────────────────────────────────────────────────────────

/// Return detected hardware / capability information to the frontend.
#[tauri::command]
fn detect_hardware() -> hardware::HardwareInfo {
    hardware::detect_hardware()
}

/// Alias exposed as `check_prerequisites` for clarity in the frontend.
#[tauri::command]
fn check_prerequisites() -> hardware::HardwareInfo {
    hardware::detect_hardware()
}

/// Validate the current wizard step and return the result.
#[tauri::command]
fn advance_wizard_step(state: wizard::WizardState) -> wizard::WizardStepResult {
    wizard::advance_step(&state)
}

/// Load and return the persisted application settings.
#[tauri::command]
fn get_settings(app: tauri::AppHandle) -> settings::AppSettings {
    let config_path = app
        .path()
        .app_config_dir()
        .map(|p| p.join("settings.json"))
        .unwrap_or_else(|_| std::path::PathBuf::from("settings.json"));
    settings::AppSettings::load(&config_path)
}

/// Validate and persist the application settings.
#[tauri::command]
fn save_settings(
    app: tauri::AppHandle,
    s: settings::AppSettings,
) -> Result<(), String> {
    s.validate()?;
    let config_path = app
        .path()
        .app_config_dir()
        .map(|p| p.join("settings.json"))
        .unwrap_or_else(|_| std::path::PathBuf::from("settings.json"));
    s.save(&config_path)
}

// ── Entry point ───────────────────────────────────────────────────────────────

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            detect_hardware,
            check_prerequisites,
            advance_wizard_step,
            get_settings,
            save_settings,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
