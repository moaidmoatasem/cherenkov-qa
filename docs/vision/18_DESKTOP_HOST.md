# Vision 18: Desktop Host (Tauri 2, Hardware Detection, Setup Wizard)

**Date:** 2026-06-08
**Status:** Active
**Related EPIC:** #282 (Phase 3)

---

## Overview

The Desktop Host is CHERENKOV's native application — a Tauri 2 app that provides one-click installation, hardware detection, and a 7-step setup wizard. It enables:

- **One-click installation**: MSI (Windows), DMG (macOS), AppImage (Linux)
- **Hardware detection**: GPU/CPU/RAM → DeviceClass → VLMTier
- **7-step setup wizard**: Hardware scan → Engine selection → Model download → Device targets → Project bootstrap → Engine config → Confirmation
- **Device management**: Emulators, physical devices, browsers
- **Settings UI**: VLM tier, Redis, egress policy
- **Sidecar IPC**: NDJSON protocol with CHERENKOV CLI

---

## Architecture

```
┌─────────────────────────────────────┐
│  Tauri 2 Desktop App (Rust)         │
│  - Window management                │
│  - Hardware detection               │
│  - Device management                │
│  - Settings UI                      │
└──────────────┬──────────────────────┘
               │ NDJSON (stdin/stdout)
               │ Commands: run, stop, status, config_set, config_get
               │ Events: progress, result, error, health_change
               ▼
┌─────────────────────────────────────┐
│  CHERENKOV CLI (PyInstaller)        │
│  - Pipeline execution               │
│  - Knowledge queries                │
│  - Chat agent                       │
│  - Mobile testing                   │
└─────────────────────────────────────┘
```

---

## Tauri 2 main.rs

```rust
// desktop/src-tauri/src/main.rs
use tauri::Manager;
use std::process::{Command, Child, Stdio};
use std::io::{BufRead, BufReader};
use std::sync::{Arc, Mutex};

struct AppState {
    sidecar: Arc<Mutex<Option<Child>>>,
}

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            sidecar: Arc::new(Mutex::new(None)),
        })
        .invoke_handler(tauri::generate_handler![
            start_sidecar,
            stop_sidecar,
            get_status,
            config_set,
            config_get
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn start_sidecar(state: tauri::State<AppState>) -> Result<(), String> {
    let mut sidecar = state.sidecar.lock().unwrap();

    if sidecar.is_some() {
        return Err("Sidecar already running".to_string());
    }

    let child = Command::new("cherenkov")
        .arg("review")
        .arg("--port")
        .arg("8000")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start sidecar: {}", e))?;

    *sidecar = Some(child);
    Ok(())
}

#[tauri::command]
fn stop_sidecar(state: tauri::State<AppState>) -> Result<(), String> {
    let mut sidecar = state.sidecar.lock().unwrap();

    if let Some(mut child) = sidecar.take() {
        child.kill().map_err(|e| format!("Failed to kill sidecar: {}", e))?;
    }

    Ok(())
}

#[tauri::command]
fn get_status() -> Result<String, String> {
    let response = reqwest::blocking::get("http://localhost:8000/healthz")
        .map_err(|e| format!("Failed to get status: {}", e))?;

    Ok(response.text().unwrap())
}

#[tauri::command]
fn config_set(key: String, value: String) -> Result<(), String> {
    // Update cherenkov.toml
    Ok(())
}

#[tauri::command]
fn config_get(key: String) -> Result<String, String> {
    // Read from cherenkov.toml
    Ok(String::new())
}
```

---

## Hardware Detection

```rust
// desktop/src-tauri/src/hardware.rs
use std::process::Command;

pub enum DeviceClass {
    GpuWorkstation,
    GpuMidRange,
    GpuEntry,
    CpuHighEnd,
    CpuStandard,
    CpuConstrained,
    Unknown,
}

pub fn detect_device_class() -> DeviceClass {
    if let Some(gpu) = detect_gpu() {
        if gpu.contains("RTX 3090") || gpu.contains("RTX 4090") {
            return DeviceClass::GpuWorkstation;
        } else if gpu.contains("RTX 3060") || gpu.contains("RTX 3070") || gpu.contains("RTX 3080") {
            return DeviceClass::GpuMidRange;
        } else if gpu.contains("GTX 1660") || gpu.contains("RTX 2060") {
            return DeviceClass::GpuEntry;
        }
    }

    let cpu_cores = detect_cpu_cores();
    let ram_gb = detect_ram_gb();

    if cpu_cores >= 16 && ram_gb >= 32 {
        DeviceClass::CpuHighEnd
    } else if cpu_cores >= 8 && ram_gb >= 16 {
        DeviceClass::CpuStandard
    } else if cpu_cores >= 4 && ram_gb >= 8 {
        DeviceClass::CpuConstrained
    } else {
        DeviceClass::Unknown
    }
}

fn detect_gpu() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        let output = Command::new("wmic")
            .args(&["path", "win32_VideoController", "get", "name"])
            .output()
            .ok()?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        return Some(stdout.to_string());
    }

    #[cfg(target_os = "linux")]
    {
        let output = Command::new("lspci")
            .output()
            .ok()?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        for line in stdout.lines() {
            if line.contains("VGA") || line.contains("3D") {
                return Some(line.to_string());
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        let output = Command::new("system_profiler")
            .arg("SPDisplaysDataType")
            .output()
            .ok()?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        return Some(stdout.to_string());
    }

    None
}

fn detect_cpu_cores() -> usize {
    num_cpus::get()
}

fn detect_ram_gb() -> usize {
    let total_bytes = sys_info::mem_info().map(|m| m.total).unwrap_or(0);
    (total_bytes / 1024 / 1024 / 1024) as usize
}
```

---

## OS-Specific Setup

### mod.rs

```rust
// desktop/src-tauri/src/setup/mod.rs
pub mod windows;
pub mod macos;
pub mod linux;

pub trait Setup {
    fn check_prerequisites() -> Vec<Prerequisite>;
    fn install_prerequisite(name: &str) -> Result<(), String>;
}

pub struct Prerequisite {
    pub name: String,
    pub installed: bool,
    pub install_command: String,
}
```

### windows.rs

```rust
// desktop/src-tauri/src/setup/windows.rs
use super::{Setup, Prerequisite};
use std::process::Command;

pub struct WindowsSetup;

impl Setup for WindowsSetup {
    fn check_prerequisites() -> Vec<Prerequisite> {
        vec![
            check_ollama(),
            check_node(),
            check_docker(),
            check_adb(),
            check_maestro(),
        ]
    }

    fn install_prerequisite(name: &str) -> Result<(), String> {
        match name {
            "ollama" => install_ollama_windows(),
            "node" => install_node_windows(),
            "docker" => install_docker_windows(),
            "adb" => install_adb_windows(),
            "maestro" => install_maestro_windows(),
            _ => Err(format!("Unknown prerequisite: {}", name)),
        }
    }
}

fn check_ollama() -> Prerequisite {
    let installed = Command::new("ollama")
        .arg("--version")
        .output()
        .is_ok();

    Prerequisite {
        name: "ollama".to_string(),
        installed,
        install_command: "winget install Ollama.Ollama".to_string(),
    }
}

fn check_node() -> Prerequisite {
    let installed = Command::new("node")
        .arg("--version")
        .output()
        .is_ok();

    Prerequisite {
        name: "node".to_string(),
        installed,
        install_command: "winget install OpenJS.NodeJS".to_string(),
    }
}

// ... similar for docker, adb, maestro
```

---

## 7-Step Setup Wizard

```tsx
// desktop/src/ui/OnboardingWizard.tsx
import React, { useState } from 'react';

const STEPS = [
  'Hardware Scan',
  'Engine Selection',
  'Model Download',
  'Device Targets',
  'Project Bootstrap',
  'Engine Config',
  'Confirmation'
];

export function OnboardingWizard() {
  const [currentStep, setCurrentStep] = useState(0);

  return (
    <div className="wizard">
      <div className="wizard-steps">
        {STEPS.map((step, i) => (
          <div key={i} className={i === currentStep ? 'active' : ''}>
            {step}
          </div>
        ))}
      </div>

      <div className="wizard-content">
        {currentStep === 0 && <HardwareScanStep onNext={() => setCurrentStep(1)} />}
        {currentStep === 1 && <EngineSelectionStep onNext={() => setCurrentStep(2)} />}
        {currentStep === 2 && <ModelDownloadStep onNext={() => setCurrentStep(3)} />}
        {currentStep === 3 && <DeviceTargetsStep onNext={() => setCurrentStep(4)} />}
        {currentStep === 4 && <ProjectBootstrapStep onNext={() => setCurrentStep(5)} />}
        {currentStep === 5 && <EngineConfigStep onNext={() => setCurrentStep(6)} />}
        {currentStep === 6 && <ConfirmationStep onComplete={() => alert('Setup complete!')} />}
      </div>
    </div>
  );
}

function HardwareScanStep({ onNext }) {
  return (
    <div>
      <h2>Hardware Scan</h2>
      <p>Detecting your hardware...</p>
      <p>Device Class: GPU Mid-Range</p>
      <p>Recommended VLM Tier: Mid (qwen2.5-vl:3b)</p>
      <button onClick={onNext}>Next</button>
    </div>
  );
}

function EngineSelectionStep({ onNext }) {
  return (
    <div>
      <h2>Engine Selection</h2>
      <label>
        <input type="radio" name="engine" value="ollama" />
        Ollama (local, no Docker)
      </label>
      <label>
        <input type="radio" name="engine" value="localai" />
        LocalAI (Docker, VLM built-in)
      </label>
      <label>
        <input type="radio" name="engine" value="demo" />
        Demo Mode (no LLM, cached responses)
      </label>
      <button onClick={onNext}>Next</button>
    </div>
  );
}

// ... similar for other steps
```

---

## DeviceManager Screen

```tsx
// desktop/src/ui/DeviceManager.tsx
import React, { useState, useEffect } from 'react';

interface Device {
  id: string;
  name: string;
  type: 'emulator' | 'physical' | 'browser';
  status: 'connected' | 'disconnected' | 'error';
  platform: 'android' | 'ios' | 'web';
}

export function DeviceManager() {
  const [devices, setDevices] = useState<Device[]>([]);

  useEffect(() => {
    fetch('/api/v1/devices')
      .then(r => r.json())
      .then(setDevices);
  }, []);

  return (
    <div className="device-manager">
      <h2>Device Manager</h2>

      <div className="device-section">
        <h3>Emulators</h3>
        {devices.filter(d => d.type === 'emulator').map(device => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </div>

      <div className="device-section">
        <h3>Physical Devices</h3>
        {devices.filter(d => d.type === 'physical').map(device => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </div>

      <div className="device-section">
        <h3>Browser Targets</h3>
        {devices.filter(d => d.type === 'browser').map(device => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </div>
    </div>
  );
}

function DeviceCard({ device }: { device: Device }) {
  const statusColor = device.status === 'connected' ? 'green' :
                      device.status === 'error' ? 'red' : 'gray';

  return (
    <div className="device-card">
      <div className="device-status" style={{ color: statusColor }}>
        ● {device.status}
      </div>
      <div className="device-name">{device.name}</div>
      <div className="device-platform">{device.platform}</div>
      <button>Test Connection</button>
    </div>
  );
}
```

---

## Settings Screen

```tsx
// desktop/src/ui/Settings.tsx
import React, { useState, useEffect } from 'react';

interface Settings {
  vlm_tier: string;
  vlm_provider: string;
  redis_enabled: boolean;
  redis_url: string;
  egress_policy: 'none' | 'internal' | 'any';
}

export function Settings() {
  const [settings, setSettings] = useState<Settings>({
    vlm_tier: 'small',
    vlm_provider: 'localai',
    redis_enabled: false,
    redis_url: '',
    egress_policy: 'none',
  });

  useEffect(() => {
    fetch('/api/v1/settings')
      .then(r => r.json())
      .then(setSettings);
  }, []);

  const saveSettings = () => {
    fetch('/api/v1/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
  };

  return (
    <div className="settings">
      <h2>Settings</h2>

      <div className="settings-section">
        <h3>VLM Configuration</h3>
        <label>
          VLM Tier:
          <select value={settings.vlm_tier} onChange={e => setSettings({...settings, vlm_tier: e.target.value})}>
            <option value="frontier">Frontier (qwen2.5-vl:7b)</option>
            <option value="mid">Mid (qwen2.5-vl:3b)</option>
            <option value="small">Small (qwen2.5-vl:1.5b)</option>
            <option value="pixel_diff_only">Pixel Diff Only (no VLM)</option>
          </select>
        </label>
        <label>
          VLM Provider:
          <select value={settings.vlm_provider} onChange={e => setSettings({...settings, vlm_provider: e.target.value})}>
            <option value="localai">LocalAI (Docker)</option>
            <option value="ollama">Ollama (local)</option>
            <option value="openai">OpenAI (cloud)</option>
          </select>
        </label>
      </div>

      <div className="settings-section">
        <h3>Redis Configuration</h3>
        <label>
          <input type="checkbox" checked={settings.redis_enabled} onChange={e => setSettings({...settings, redis_enabled: e.target.checked})} />
          Enable Redis
        </label>
        {settings.redis_enabled && (
          <label>
            Redis URL:
            <input type="text" value={settings.redis_url} onChange={e => setSettings({...settings, redis_url: e.target.value})} />
          </label>
        )}
      </div>

      <div className="settings-section">
        <h3>Egress Policy</h3>
        <label>
          <input type="radio" name="egress" value="none" checked={settings.egress_policy === 'none'} onChange={e => setSettings({...settings, egress_policy: e.target.value})} />
          None (no outbound network)
        </label>
        <label>
          <input type="radio" name="egress" value="internal" checked={settings.egress_policy === 'internal'} onChange={e => setSettings({...settings, egress_policy: e.target.value})} />
          Internal (localhost only)
        </label>
        <label>
          <input type="radio" name="egress" value="any" checked={settings.egress_policy === 'any'} onChange={e => setSettings({...settings, egress_policy: e.target.value})} />
          Any (allow cloud APIs)
        </label>
      </div>

      <button onClick={saveSettings}>Save Settings</button>
    </div>
  );
}
```

---

## IPC Protocol

```rust
// desktop/src-tauri/src/ipc.rs
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout};

#[derive(Serialize, Deserialize)]
pub struct IPCMessage {
    pub event: String,
    pub data: serde_json::Value,
}

pub struct IPCChannel {
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

impl IPCChannel {
    pub fn new(child: &mut Child) -> Self {
        let stdin = child.stdin.take().expect("Failed to open stdin");
        let stdout = child.stdout.take().expect("Failed to open stdout");

        IPCChannel {
            stdin,
            stdout: BufReader::new(stdout),
        }
    }

    pub fn send(&mut self, message: IPCMessage) -> Result<(), String> {
        let json = serde_json::to_string(&message)
            .map_err(|e| format!("Failed to serialize: {}", e))?;

        writeln!(self.stdin, "{}", json)
            .map_err(|e| format!("Failed to write: {}", e))?;

        self.stdin.flush()
            .map_err(|e| format!("Failed to flush: {}", e))?;

        Ok(())
    }

    pub fn receive(&mut self) -> Result<IPCMessage, String> {
        let mut line = String::new();
        self.stdout.read_line(&mut line)
            .map_err(|e| format!("Failed to read: {}", e))?;

        let message: IPCMessage = serde_json::from_str(&line)
            .map_err(|e| format!("Failed to parse: {}", e))?;

        Ok(message)
    }
}
```

---

## Desktop Packaging

### tauri.conf.json

```json
{
  "tauri": {
    "bundle": {
      "active": true,
      "targets": ["msi", "dmg", "appimage"],
      "identifier": "com.cherenkov.desktop",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ]
    }
  }
}
```

### CI/CD Pipeline

```yaml
# .github/workflows/desktop-release.yml
name: Desktop Release
on:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - name: Build desktop app
        run: cd desktop && cargo tauri build
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: cherenkov-${{ matrix.os }}
          path: desktop/src-tauri/target/release/bundle/
```

---

## References

- EPIC #282 (Phase 3: Desktop Host)
- ADR-002 (Tauri 2 + PyInstaller sidecar)
- Issue #345-#353 (Desktop host tickets)
- `docs/PHASE_PLAN.md` (Phase 3 details)
- `desktop/src-tauri/src/main.rs` (to be rewritten)
- Tauri 2 documentation: https://v2.tauri.app/
