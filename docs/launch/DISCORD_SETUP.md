# CHERENKOV Discord Community Setup

This document serves as the architectural blueprint for the official CHERENKOV Discord server. As we launch v1.1.0 and step into the Reality Engine phase, cultivating a technical, high-signal community is paramount.

## 1. Server Architecture (Channels)

### 📣 INFORMATION
- #announcements - Official release notes, phase completions, and major product updates. (Read-only)
- #welcome-and-rules - Server rules and onboarding instructions. (Read-only)
- #getting-started - Links to Quick Start guide, docs, and GitHub repo. (Read-only)

### 💬 CHERENKOV HUB
- #general - High-level discussion about API testing, drift detection, and the Reality Engine vision.
- #showcase - Share your successful cherenkov validate runs and the drift you caught in your live servers.

### 🛠️ SUPPORT & USAGE
- #help-cli - Troubleshooting the core CLI, alidate, and init commands.
- #help-vlm - Discussions on LocalAI, Ollama, and Vision-Language Model integrations.
- #help-integrations - CI/CD pipeline issues, Jira exports, and VS Code extension help.

### 💻 DEVELOPMENT (Core Contributors)
- #contributing - Discussion on PRs, architecture, and roadmap (Phase 13+).
- #core-dev - Deep technical dive into SpecDriftDetector, generation templates, and test validation.

---

## 2. Roles & Permissions

- **Admin/Maintainer**: Full access. (Color: Red/Pink #e91e63)
- **Core Contributor**: Given to users with merged PRs. Can bypass slowmode. (Color: Gold #f1c40f)
- **Early Adopter**: Special vanity role given to the first 500 members to join after the v1.1.0 launch. (Color: Purple #9b59b6)
- **Member**: Default role. (Color: Default)

---

## 3. Welcome Message (For Onboarding Bot)

**Title:** Welcome to the Reality Engine! ⚛️

**Body:**
Welcome to the official CHERENKOV community! We're building the model-agnostic Reality Engine to keep your APIs, specs, and live traffic in perfect sync.

**Getting Started:**
1. Star the repo on GitHub: https://github.com/moaidmoatasem/cherenkov-qa
2. Try the Quick Start: 
px cherenkov-cli init
3. If you run into any issues, head over to #help-cli.

*If you're here from Product Hunt or Hacker News, let us know what you're working on in #general!*
