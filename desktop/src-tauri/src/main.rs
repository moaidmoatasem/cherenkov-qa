#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod file_watcher;
mod hardware;
mod settings;
mod setup_wizard;
mod updater;
mod wizard;

use serde::Deserialize;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

// ── Sidecar state ────────────────────────────────────────────────────────────

#[derive(Debug, Default)]
struct SidecarState {
    port: Option<u16>,
    child: Option<CommandChild>,
}

type SharedSidecar = Arc<Mutex<SidecarState>>;

// ── NDJSON events from launcher.py ───────────────────────────────────────────

#[derive(Debug, Deserialize)]
#[serde(tag = "event", content = "data", rename_all = "snake_case")]
enum LauncherEvent {
    Ready { version: String },
    Port { port: u16 },
    Shutdown {
        #[allow(dead_code)]
        signal: serde_json::Value,
    },
    Progress { step: String, pct: u8, detail: Option<String> },
    DemoMode { reason: String },
}

// ── Tauri commands ────────────────────────────────────────────────────────────

#[tauri::command]
async fn get_api_port(state: State<'_, SharedSidecar>) -> Result<u16, String> {
    let guard = state.lock().map_err(|e| e.to_string())?;
    guard.port.ok_or_else(|| "Engine not ready yet".to_string())
}

#[tauri::command]
async fn run_setup_wizard(app: AppHandle, model: String) -> Result<setup_wizard::SetupState, String> {
    Ok(setup_wizard::run_setup(app, model).await)
}

#[tauri::command]
async fn watch_spec_dir(app: AppHandle, path: String) -> Result<(), String> {
    file_watcher::start_watcher(app, PathBuf::from(path))
}

#[tauri::command]
async fn check_for_updates(app: AppHandle) {
    updater::check_and_notify(app).await;
}

#[tauri::command]
async fn install_update(app: AppHandle) {
    updater::install_update(app).await;
}

#[tauri::command]
fn detect_hardware() -> hardware::HardwareInfo {
    hardware::detect_hardware()
}

#[tauri::command]
fn check_prerequisites() -> hardware::HardwareInfo {
    hardware::detect_hardware()
}

#[tauri::command]
fn advance_wizard_step(state: wizard::WizardState) -> wizard::WizardStepResult {
    wizard::advance_step(&state)
}

#[tauri::command]
fn get_settings(app: tauri::AppHandle) -> settings::AppSettings {
    let config_path = app
        .path()
        .app_config_dir()
        .map(|p| p.join("settings.json"))
        .unwrap_or_else(|_| std::path::PathBuf::from("settings.json"));
    settings::AppSettings::load(&config_path)
}

#[tauri::command]
fn save_settings(app: tauri::AppHandle, s: settings::AppSettings) -> Result<(), String> {
    s.validate()?;
    let config_path = app
        .path()
        .app_config_dir()
        .map(|p| p.join("settings.json"))
        .unwrap_or_else(|_| std::path::PathBuf::from("settings.json"));
    s.save(&config_path)
}

// ── Health check polling ──────────────────────────────────────────────────────

async fn wait_for_health(port: u16, max_attempts: u32) -> bool {
    let client = reqwest::Client::new();
    let url = format!("http://127.0.0.1:{}/healthz", port);
    for _ in 0..max_attempts {
        if let Ok(resp) = client.get(&url).timeout(Duration::from_secs(2)).send().await {
            if resp.status().is_success() {
                return true;
            }
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    false
}

// ── Sidecar spawn + NDJSON reader ─────────────────────────────────────────────

fn spawn_sidecar(app: &AppHandle, sidecar_state: SharedSidecar) {
    let app_clone = app.clone();

    tauri::async_runtime::spawn(async move {
        let shell = app_clone.shell();
        let (mut rx, child) = match shell
            .sidecar("cherenkov-launcher")
            .expect("cherenkov-launcher sidecar not configured")
            .env("CHERENKOV_NO_BROWSER", "1")
            .spawn()
        {
            Ok(pair) => pair,
            Err(e) => {
                eprintln!("[sidecar] failed to spawn: {e}");
                let _ = app_clone.emit("engine-error", format!("Failed to start engine: {e}"));
                return;
            }
        };

        {
            let mut guard = sidecar_state.lock().unwrap();
            guard.child = Some(child);
        }

        let _ = app_clone.emit("engine-starting", ());

        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    if let Ok(evt) = serde_json::from_str::<LauncherEvent>(line_str.trim()) {
                        match evt {
                            LauncherEvent::Ready { version } => {
                                let _ = app_clone.emit("engine-ready", version);
                            }
                            LauncherEvent::Port { port } => {
                                {
                                    let mut guard = sidecar_state.lock().unwrap();
                                    guard.port = Some(port);
                                }
                                let app2 = app_clone.clone();
                                tokio::spawn(async move {
                                    if wait_for_health(port, 30).await {
                                        let _ = app2.emit("engine-healthy", port);
                                        // The window URL in tauri.conf.json assumes port 8000;
                                        // navigate to the port the engine actually bound.
                                        if port != 8000 {
                                            if let Some(window) = app2.get_webview_window("main") {
                                                if let Ok(url) = format!("http://127.0.0.1:{}", port).parse() {
                                                    let _ = window.navigate(url);
                                                }
                                            }
                                        }
                                    } else {
                                        let _ = app2.emit("engine-error", "Engine health check timed out");
                                    }
                                });
                            }
                            LauncherEvent::DemoMode { reason } => {
                                let _ = app_clone.emit("engine-demo-mode", reason);
                            }
                            LauncherEvent::Shutdown { .. } => {
                                let _ = app_clone.emit("engine-stopped", ());
                            }
                            LauncherEvent::Progress { step, pct, detail } => {
                                let _ = app_clone.emit("engine-progress", serde_json::json!({
                                    "step": step, "pct": pct, "detail": detail
                                }));
                            }
                        }
                    } else {
                        eprintln!("[engine] {}", line_str.trim());
                    }
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[engine:err] {}", String::from_utf8_lossy(&line).trim());
                }
                CommandEvent::Error(e) => {
                    eprintln!("[sidecar] error: {e}");
                    let _ = app_clone.emit("engine-error", e);
                }
                CommandEvent::Terminated(status) => {
                    eprintln!("[sidecar] terminated: {:?}", status);
                    let _ = app_clone.emit("engine-stopped", ());
                    break;
                }
                _ => {}
            }
        }
    });
}

// ── Entry point ───────────────────────────────────────────────────────────────

fn main() {
    let sidecar_state: SharedSidecar = Arc::new(Mutex::new(SidecarState::default()));

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_process::init())
        .manage(sidecar_state.clone())
        .setup(move |app| {
            let handle = app.handle().clone();
            let state = sidecar_state.clone();
            spawn_sidecar(&handle, state);
            let handle2 = handle.clone();
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(Duration::from_secs(5)).await;
                updater::check_and_notify(handle2).await;
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let _ = window.app_handle().emit("app-closing", ());
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_api_port,
            run_setup_wizard,
            watch_spec_dir,
            check_for_updates,
            install_update,
            detect_hardware,
            check_prerequisites,
            advance_wizard_step,
            get_settings,
            save_settings,
        ])
        .run(tauri::generate_context!())
        .expect("error while running CHERENKOV desktop app");
}
