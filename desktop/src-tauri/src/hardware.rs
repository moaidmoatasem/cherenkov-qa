use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub enum DeviceClass {
    Desktop,
    Laptop,
    Server,
    Android,
    Ios,
    Unknown,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HardwareInfo {
    pub device_class: DeviceClass,
    pub os: String,
    pub arch: String,
    pub cpu_cores: usize,
    pub has_adb: bool,
    pub has_maestro: bool,
    pub has_node: bool,
    pub has_python: bool,
    pub has_ollama: bool,
}

/// Check whether a binary is available on PATH.
fn has_binary(bin: &str) -> bool {
    #[cfg(target_os = "windows")]
    let checker = "where";
    #[cfg(not(target_os = "windows"))]
    let checker = "which";

    std::process::Command::new(checker)
        .arg(bin)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

/// Heuristically classify the device. Without access to chassis type from
/// userspace in a cross-platform way, we make a simple inference:
/// - Linux CI / headless → Server
/// - macOS / Windows     → Desktop (conservative fallback; laptops are a
///                         superset of desktops for capability purposes)
fn classify_device(os: &str) -> DeviceClass {
    match os {
        "linux" => {
            // If no display server is present, treat as Server.
            let has_display = std::env::var("DISPLAY").is_ok()
                || std::env::var("WAYLAND_DISPLAY").is_ok();
            if has_display {
                DeviceClass::Desktop
            } else {
                DeviceClass::Server
            }
        }
        "macos" | "windows" => DeviceClass::Desktop,
        _ => DeviceClass::Unknown,
    }
}

pub fn detect_hardware() -> HardwareInfo {
    let os = std::env::consts::OS.to_string();
    let arch = std::env::consts::ARCH.to_string();
    let cpu_cores = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1);
    let device_class = classify_device(&os);

    HardwareInfo {
        device_class,
        os,
        arch,
        cpu_cores,
        has_adb: has_binary("adb"),
        has_maestro: has_binary("maestro"),
        has_node: has_binary("node"),
        has_python: has_binary("python3") || has_binary("python"),
        has_ollama: has_binary("ollama"),
    }
}
