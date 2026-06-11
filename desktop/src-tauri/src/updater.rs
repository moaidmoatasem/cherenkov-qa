use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};
use tauri_plugin_updater::UpdaterExt;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub version: String,
    pub notes: Option<String>,
    pub download_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "status")]
pub enum UpdateStatus {
    Checking,
    Available { info: UpdateInfo },
    UpToDate,
    Downloading { progress_pct: u8 },
    Installing,
    Error { message: String },
}

/// Check for updates and emit events to the frontend.
pub async fn check_and_notify(app: AppHandle) {
    let _ = app.emit("update-status", UpdateStatus::Checking);

    let updater = match app.updater() {
        Ok(u) => u,
        Err(e) => {
            let _ = app.emit("update-status", UpdateStatus::Error {
                message: e.to_string(),
            });
            return;
        }
    };

    match updater.check().await {
        Ok(Some(update)) => {
            let info = UpdateInfo {
                version: update.version.clone(),
                notes: update.body.clone(),
                download_url: update.download_url.to_string(),
            };
            let _ = app.emit("update-status", UpdateStatus::Available { info });
        }
        Ok(None) => {
            let _ = app.emit("update-status", UpdateStatus::UpToDate);
        }
        Err(e) => {
            let _ = app.emit("update-status", UpdateStatus::Error {
                message: e.to_string(),
            });
        }
    }
}

/// Download and install the pending update. Frontend triggers this after user confirms.
pub async fn install_update(app: AppHandle) {
    let updater = match app.updater() {
        Ok(u) => u,
        Err(e) => {
            let _ = app.emit("update-status", UpdateStatus::Error {
                message: e.to_string(),
            });
            return;
        }
    };

    let update = match updater.check().await {
        Ok(Some(u)) => u,
        Ok(None) => return,
        Err(e) => {
            let _ = app.emit("update-status", UpdateStatus::Error {
                message: e.to_string(),
            });
            return;
        }
    };

    let app_clone = app.clone();
    let download_result = update.download_and_install(
        move |chunk_length, content_length| {
            if let Some(total) = content_length {
                let pct = ((chunk_length as f64 / total as f64) * 100.0) as u8;
                let _ = app_clone.emit("update-status", UpdateStatus::Downloading {
                    progress_pct: pct,
                });
            }
        },
        move || {},
    ).await;

    match download_result {
        Ok(_) => {
            let _ = app.emit("update-status", UpdateStatus::Installing);
            // Restart the app after install
            app.restart();
        }
        Err(e) => {
            let _ = app.emit("update-status", UpdateStatus::Error {
                message: e.to_string(),
            });
        }
    }
}
