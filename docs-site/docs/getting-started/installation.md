---
title: Installation
description: Install CHERENKOV-QA via pip, npx, or Docker. Prerequisites and environment setup.
---

# Installation

## Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.10+ | Required for the core engine |
| Node.js | 18+ | Required for Playwright test execution |
| Ollama | Latest | Required for local LLM generation |
| Docker | 20+ | Optional — for LocalAI, Redis, Prism |

---

## 1. Clone and Set Up

```bash
git clone https://github.com/moaidmoatasem/cherenkov-qa.git
cd cherenkov-qa

# Create a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install Node/Playwright in the test stub folder
cd stub
npm install
npx playwright install
cd ..
```

---

## 2. Install Ollama + Model

CHERENKOV uses a local LLM by default. No cloud. No API keys.

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the default models
ollama pull qwen2.5-coder:7b     # Code generation (7B params, ~4GB)
ollama pull deepseek-r1:8b       # Reasoning/planning (8B params, ~5GB)
```

!!! tip "GPU not required"
    Both models run on CPU. GPU acceleration (NVIDIA/AMD/Apple Silicon) dramatically speeds up generation but is optional.

---

## 3. Docker Setup (Recommended for Full Stack)

Run the complete environment — Python engine, React dashboard, target API, and Ollama — with a single command.

```bash
# Full environment (recommended)
make full

# Demo mode (no GPU, no model download — uses mock data)
make demo
```

Dashboard available at `http://localhost:8000` after startup.

---

## 4. Verify Installation

```bash
# Check Python engine
cherenkov --version
# Expected: cherenkov 1.1.0

# Check test framework
cd stub && npx playwright --version
# Expected: Version 1.x.x

# Verify Ollama
ollama list
# Expected: qwen2.5-coder:7b and deepseek-r1:8b listed
```

---

## Platform Notes

=== "Linux (Ubuntu/Debian)"

    All features fully supported. Recommended platform.

    ```bash
    # Optional: install Tauri desktop dependencies
    sudo apt install -y build-essential pkg-config libwebkit2gtk-4.1-dev \
      libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

    # Optional: install ADB for mobile testing
    sudo apt install -y android-tools-adb

    # Optional: install Maestro for mobile flows
    curl -Ls https://get.maestro.mobile.dev | bash
    ```

=== "macOS"

    Core features supported. Desktop app requires `cargo` + Xcode Command Line Tools.

    ```bash
    brew install ollama
    brew install --cask docker
    ```

=== "Windows (WSL2)"

    Run everything inside WSL2 Ubuntu. The CLI, Playwright, and Ollama all work in WSL.

    ```powershell
    # Install WSL2 Ubuntu
    wsl --install -d Ubuntu-24.04
    ```

    Then follow the Linux steps inside WSL.

---

## Next Steps

[Run your first validation →](quickstart.md){ .md-button .md-button--primary }
