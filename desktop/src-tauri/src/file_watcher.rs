use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::mpsc;
use std::time::Duration;
use tauri::{AppHandle, Emitter};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpecChanged {
    pub path: String,
    pub kind: String,
}

/// Start watching a directory for OpenAPI spec file changes.
/// Emits `spec-changed` events to the Tauri frontend when .yaml/.json files change.
pub fn start_watcher(app: AppHandle, watch_path: PathBuf) -> Result<(), String> {
    let (tx, rx) = mpsc::channel::<notify::Result<Event>>();

    let mut watcher = RecommendedWatcher::new(
        move |res| { let _ = tx.send(res); },
        Config::default().with_poll_interval(Duration::from_secs(2)),
    )
    .map_err(|e| e.to_string())?;

    watcher
        .watch(&watch_path, RecursiveMode::Recursive)
        .map_err(|e| e.to_string())?;

    std::thread::spawn(move || {
        // Keep watcher alive in this thread
        let _watcher = watcher;

        for res in rx {
            match res {
                Ok(event) => {
                    // Only care about modify/create events on spec files
                    let is_write = matches!(
                        event.kind,
                        EventKind::Modify(_) | EventKind::Create(_)
                    );
                    if !is_write {
                        continue;
                    }

                    for path in &event.paths {
                        let ext = path.extension()
                            .and_then(|e| e.to_str())
                            .unwrap_or("");
                        if matches!(ext, "yaml" | "yml" | "json") {
                            let payload = SpecChanged {
                                path: path.display().to_string(),
                                kind: format!("{:?}", event.kind),
                            };
                            let _ = app.emit("spec-changed", payload);
                        }
                    }
                }
                Err(e) => {
                    eprintln!("[file_watcher] error: {:?}", e);
                }
            }
        }
    });

    Ok(())
}
