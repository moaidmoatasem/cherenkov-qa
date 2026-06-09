use serde::{Deserialize, Serialize};

/// 7-step setup wizard state passed from the frontend via `invoke()`.
#[derive(Debug, Serialize, Deserialize)]
pub struct WizardState {
    /// Current step (1-7).
    pub step: u8,
    /// Steps that have already been completed.
    pub completed: Vec<u8>,
    /// Arbitrary JSON payload supplied by the frontend for the current step.
    pub data: serde_json::Value,
}

/// Result returned to the frontend after attempting to advance a wizard step.
#[derive(Debug, Serialize, Deserialize)]
pub struct WizardStepResult {
    pub success: bool,
    pub message: String,
    /// The step the wizard should move to next, or `None` when the wizard is
    /// complete (after step 7).
    pub next_step: Option<u8>,
}

// ── Step names (for human-readable messages) ─────────────────────────────────

fn step_name(step: u8) -> &'static str {
    match step {
        1 => "Check Prerequisites",
        2 => "Select Work Directory",
        3 => "Configure LLM",
        4 => "Configure Egress",
        5 => "Test Connection",
        6 => "Select Devices",
        7 => "Complete",
        _ => "Unknown",
    }
}

// ── Per-step validation helpers ───────────────────────────────────────────────

/// Step 1 – Check prerequisites.
/// The frontend is expected to have already run `check_prerequisites` and
/// stored the `HardwareInfo` payload in `state.data`.  We only check that
/// `has_node` is true because Node is the minimum hard requirement for the
/// desktop shell.
fn validate_step1(data: &serde_json::Value) -> Result<(), String> {
    if let Some(has_node) = data.get("has_node").and_then(|v| v.as_bool()) {
        if !has_node {
            return Err("Node.js was not found on PATH. Please install Node.js and try again.".into());
        }
    }
    Ok(())
}

/// Step 2 – Select work directory.
/// Expects `data.work_dir` to be a non-empty string.
fn validate_step2(data: &serde_json::Value) -> Result<(), String> {
    let dir = data
        .get("work_dir")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_string();
    if dir.is_empty() {
        return Err("A work directory must be selected.".into());
    }
    Ok(())
}

/// Step 3 – Configure LLM.
/// Expects `data.ollama_host` (non-empty) and optionally `data.vlm_tier`
/// ("small" | "deep").
fn validate_step3(data: &serde_json::Value) -> Result<(), String> {
    let host = data
        .get("ollama_host")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_string();
    if host.is_empty() {
        return Err("An Ollama host URL must be provided.".into());
    }
    if let Some(tier) = data.get("vlm_tier").and_then(|v| v.as_str()) {
        if tier != "small" && tier != "deep" {
            return Err(format!("vlm_tier must be \"small\" or \"deep\", got \"{}\".", tier));
        }
    }
    Ok(())
}

/// Step 4 – Configure egress policy.
/// Expects `data.egress_policy` to be one of "none" | "internal" | "any".
fn validate_step4(data: &serde_json::Value) -> Result<(), String> {
    let policy = data
        .get("egress_policy")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .trim()
        .to_string();
    match policy.as_str() {
        "none" | "internal" | "any" => Ok(()),
        "" => Err("An egress policy must be selected.".into()),
        other => Err(format!(
            "egress_policy must be \"none\", \"internal\", or \"any\", got \"{}\".",
            other
        )),
    }
}

/// Step 5 – Test connection.
/// The frontend is expected to have performed an actual connectivity check and
/// stored the result in `data.connection_ok` (bool).
fn validate_step5(data: &serde_json::Value) -> Result<(), String> {
    let ok = data
        .get("connection_ok")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if !ok {
        return Err(
            "Connection test failed. Check that the Ollama host is reachable and try again.".into(),
        );
    }
    Ok(())
}

/// Step 6 – Select devices.
/// Expects `data.devices` to be a non-empty array.
fn validate_step6(data: &serde_json::Value) -> Result<(), String> {
    let devices = data.get("devices").and_then(|v| v.as_array());
    match devices {
        Some(arr) if !arr.is_empty() => Ok(()),
        Some(_) => Err("At least one device must be selected.".into()),
        None => Err("No device list provided.".into()),
    }
}

/// Step 7 – Complete.
/// Nothing to validate; the wizard is done.
fn validate_step7(_data: &serde_json::Value) -> Result<(), String> {
    Ok(())
}

// ── Public API ────────────────────────────────────────────────────────────────

/// Validate the current wizard step and return the result, including the next
/// step number (or `None` when the wizard has finished).
pub fn advance_step(state: &WizardState) -> WizardStepResult {
    let validation = match state.step {
        1 => validate_step1(&state.data),
        2 => validate_step2(&state.data),
        3 => validate_step3(&state.data),
        4 => validate_step4(&state.data),
        5 => validate_step5(&state.data),
        6 => validate_step6(&state.data),
        7 => validate_step7(&state.data),
        n => Err(format!("Unknown wizard step: {}.", n)),
    };

    match validation {
        Ok(()) => {
            let next = if state.step >= 7 { None } else { Some(state.step + 1) };
            WizardStepResult {
                success: true,
                message: format!("Step {} ({}) completed.", state.step, step_name(state.step)),
                next_step: next,
            }
        }
        Err(msg) => WizardStepResult {
            success: false,
            message: msg,
            next_step: None,
        },
    }
}
