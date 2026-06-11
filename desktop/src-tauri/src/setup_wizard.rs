use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SetupStep {
    pub id: String,
    pub label: String,
    pub status: StepStatus,
    pub detail: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum StepStatus {
    Pending,
    Checking,
    Ok,
    Installing,
    Failed,
    Skipped,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SetupState {
    pub steps: Vec<SetupStep>,
    pub complete: bool,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SetupProgress {
    pub step_id: String,
    pub status: StepStatus,
    pub detail: Option<String>,
    pub progress_pct: Option<u8>,
}

fn emit_progress(app: &AppHandle, progress: SetupProgress) {
    let _ = app.emit("setup-progress", progress);
}

/// Check if a binary exists on PATH or at a known location.
fn is_installed(binary: &str) -> bool {
    which::which(binary).is_ok()
}

/// Check if the required model is already pulled.
pub fn is_model_available(model: &str) -> bool {
    // Check via ollama list output
    let output = std::process::Command::new("ollama")
        .args(["list"])
        .output();
    if let Ok(out) = output {
        let stdout = String::from_utf8_lossy(&out.stdout);
        return stdout.contains(model);
    }
    false
}

/// Run the full setup wizard, emitting events to the frontend.
pub async fn run_setup(app: AppHandle, required_model: String) -> SetupState {
    let steps = vec![
        check_python(&app).await,
        check_ollama(&app).await,
        check_model(&app, &required_model).await,
    ];

    let complete = steps.iter().all(|s| {
        s.status == StepStatus::Ok || s.status == StepStatus::Skipped
    });

    SetupState {
        steps,
        complete,
        error: None,
    }
}

async fn check_python(app: &AppHandle) -> SetupStep {
    emit_progress(app, SetupProgress {
        step_id: "python".into(),
        status: StepStatus::Checking,
        detail: Some("Checking Python 3.10+…".into()),
        progress_pct: None,
    });

    let found = is_installed("python3") || is_installed("python");
    let status = if found { StepStatus::Ok } else { StepStatus::Failed };
    let detail = if found {
        Some("Python found".into())
    } else {
        Some("Python 3.10+ required. Download from python.org".into())
    };

    let step = SetupStep {
        id: "python".into(),
        label: "Python 3.10+".into(),
        status: status.clone(),
        detail: detail.clone(),
    };
    emit_progress(app, SetupProgress {
        step_id: "python".into(),
        status,
        detail,
        progress_pct: None,
    });
    step
}

async fn check_ollama(app: &AppHandle) -> SetupStep {
    emit_progress(app, SetupProgress {
        step_id: "ollama".into(),
        status: StepStatus::Checking,
        detail: Some("Checking Ollama…".into()),
        progress_pct: None,
    });

    let found = is_installed("ollama");
    if found {
        let step = SetupStep {
            id: "ollama".into(),
            label: "Ollama (local LLM runtime)".into(),
            status: StepStatus::Ok,
            detail: Some("Ollama found".into()),
        };
        emit_progress(app, SetupProgress {
            step_id: "ollama".into(),
            status: StepStatus::Ok,
            detail: Some("Ollama found".into()),
            progress_pct: None,
        });
        return step;
    }

    // Ollama not found — emit download instruction
    let detail = Some("Ollama not found. Install from ollama.com, then relaunch CHERENKOV. Running in demo mode.".into());
    emit_progress(app, SetupProgress {
        step_id: "ollama".into(),
        status: StepStatus::Skipped,
        detail: detail.clone(),
        progress_pct: None,
    });

    SetupStep {
        id: "ollama".into(),
        label: "Ollama (local LLM runtime)".into(),
        status: StepStatus::Skipped,
        detail,
    }
}

async fn check_model(app: &AppHandle, model: &str) -> SetupStep {
    emit_progress(app, SetupProgress {
        step_id: "model".into(),
        status: StepStatus::Checking,
        detail: Some(format!("Checking for model {}…", model)),
        progress_pct: None,
    });

    if !is_installed("ollama") {
        let step = SetupStep {
            id: "model".into(),
            label: format!("Model: {}", model),
            status: StepStatus::Skipped,
            detail: Some("Skipped — Ollama not available".into()),
        };
        emit_progress(app, SetupProgress {
            step_id: "model".into(),
            status: StepStatus::Skipped,
            detail: Some("Skipped — Ollama not available".into()),
            progress_pct: None,
        });
        return step;
    }

    if is_model_available(model) {
        let step = SetupStep {
            id: "model".into(),
            label: format!("Model: {}", model),
            status: StepStatus::Ok,
            detail: Some(format!("{} already downloaded", model)),
        };
        emit_progress(app, SetupProgress {
            step_id: "model".into(),
            status: StepStatus::Ok,
            detail: Some(format!("{} already downloaded", model)),
            progress_pct: None,
        });
        return step;
    }

    // Pull the model
    emit_progress(app, SetupProgress {
        step_id: "model".into(),
        status: StepStatus::Installing,
        detail: Some(format!("Downloading {}… (this may take a few minutes)", model)),
        progress_pct: Some(0),
    });

    let output = tokio::process::Command::new("ollama")
        .args(["pull", model])
        .output()
        .await;

    match output {
        Ok(out) if out.status.success() => {
            let step = SetupStep {
                id: "model".into(),
                label: format!("Model: {}", model),
                status: StepStatus::Ok,
                detail: Some(format!("{} downloaded successfully", model)),
            };
            emit_progress(app, SetupProgress {
                step_id: "model".into(),
                status: StepStatus::Ok,
                detail: Some(format!("{} ready", model)),
                progress_pct: Some(100),
            });
            step
        }
        _ => {
            let step = SetupStep {
                id: "model".into(),
                label: format!("Model: {}", model),
                status: StepStatus::Failed,
                detail: Some(format!("Failed to pull {}. Running in demo mode.", model)),
            };
            emit_progress(app, SetupProgress {
                step_id: "model".into(),
                status: StepStatus::Failed,
                detail: Some(format!("Failed to pull {}. Check Ollama logs.", model)),
                progress_pct: None,
            });
            step
        }
    }
}
