# CHERENKOV QA — Video Recording Walkthrough Guide

> **Version:** 1.0 | **Date:** 2026-07-06
> **Purpose:** Step-by-step guide for recording professional onboarding and KT sessions for the CHERENKOV QA framework.

---

## Chapter 1: Recording Stack Setup

### Which Tool for Which Session?

| Session | Recommended Tool | Why |
|---------|-----------------|-----|
| **Session A** — Zero to Hero (10 min) | **asciinema** → **Loom** | Terminal-heavy; asciinema captures pure terminal, Loom adds narration overlay |
| **Session B** — Live Case: Real API (15 min) | **Loom** | Multi-pane (terminal + browser dashboard) with drawing tools |
| **Session C** — Executive Pitch (5 min) | **Loom** | Narrated slide presentation (PITCH_DECK.html in Chrome) |

---

### Option A (Recommended): Loom

**Setup:**
1. Install Loom from [loom.com/download](https://loom.com/download)
2. Sign in → choose a workspace (or create "CHERENKOV QA" workspace)
3. Open Loom settings:
   - **Quality:** 1080p (HD)
   - **Camera:** Off (code demos look better without the talking-head bubble, or enable floating bubble)
   - **Microphone:** Select your USB mic or headset (see Chapter 6 for audio setup)
   - **Trim silence:** Off (keep control; silence is useful in demos)
4. Recording mode: **Screen + Audio** (no webcam for terminal sessions; optional for Session C pitch)
5. In Loom Settings → Privacy: set recording as **"Only people with the link"** for internal KT sessions

**Before recording, test your setup:**
```
1. Click the Loom icon in the system tray
2. Select "Screen + Audio"
3. Pick the window: Windows Terminal (WSL2)
4. Click record → speak a test sentence → click stop
5. Watch the playback — check: audio levels, font size legible, no system notifications
```

---

### Option B: OBS Studio

Use OBS for recordings that need post-processing, virtual camera output, or dual-monitor note display.

**Scene setup for terminal sessions:**

1. Install OBS Studio from [obsproject.com](https://obsproject.com)
2. Create a scene called "CHERENKOV Terminal":
   - Source 1: **Window Capture** → Windows Terminal (WSL2) → crop to terminal only
   - Source 2: **Audio Input Capture** → your microphone
3. Output settings:
   - Format: MP4
   - Encoder: x264 (CRF 18 for high quality)
   - Resolution: 1920×1080
   - FPS: 30
4. Audio mixer: set mic to -3dB peak, enable noise suppression plugin

**For Session C (slide presentation):**
- Source 1: **Browser source** → PITCH_DECK.html (or Window Capture of Chrome)
- Source 2: **Audio Input Capture** → mic
- Set browser source to 1920×1080

---

### Option C: asciinema (Terminal-Only)

Perfect for Session A — creates a lightweight, shareable terminal recording that can be embedded in README files and docs.

**Install:**
```bash
pip install asciinema
# Verify
asciinema --version
```

**Quick record:**
```bash
# Start recording Session A
asciinema rec -t "CHERENKOV QA: Zero to Hero" ~/recordings/session_a.cast --overwrite

# The terminal is now recording — run the cast script:
bash ~/teamwork_projects/cherenkov_onboarding/casts/cast_session_a.sh

# Press Ctrl+D to stop recording
```

**Preview locally:**
```bash
asciinema play ~/recordings/session_a.cast
asciinema play --speed=1.5 ~/recordings/session_a.cast  # faster playback
```

---

## Chapter 2: Environment Preparation

### Recommended Screen Setup

- **Resolution:** 1920×1080 (set in Windows Display Settings → Scale: 125%)
- **Windows Terminal font:** JetBrains Mono, size 16pt, high-contrast theme (e.g., One Dark Pro)
- **Terminal window:** maximised, no tabs visible
- **DPI:** 125% scale (ensures code is legible in 1080p recording)

### Windows Terminal Settings for Recording

Open Windows Terminal Settings (Ctrl+,) and configure your Ubuntu-24.04 profile:

```json
{
  "font": {
    "face": "JetBrains Mono",
    "size": 16
  },
  "colorScheme": "One Dark Pro",
  "opacity": 100,
  "useAcrylic": false,
  "padding": "12"
}
```

> 💡 Disable the title bar and tab bar in Settings → Appearance → "Hide title bar when maximized" for a cleaner recording.

---

### Pre-Flight Checklist

Complete this checklist **before every recording session**:

**System:**
- [ ] Windows Focus Assist: **ON** (Start → Settings → System → Focus Assist → Priority only)
- [ ] Taskbar auto-hide: **ON** (Right-click taskbar → Taskbar settings → Automatically hide)
- [ ] Close: Slack, Teams, Outlook, all browser tabs except recording targets
- [ ] Disable desktop notifications: Windows Settings → Notifications → Off
- [ ] Set terminal font ≥ 16pt (JetBrains Mono recommended)

**CHERENKOV project:**
- [ ] Pull latest code: `git pull origin main` (run in WSL)
- [ ] Virtual env active: `source /home/moaid/cherenkov-qa/.venv/bin/activate`
- [ ] CHERENKOV CLI working: `/home/moaid/cherenkov-qa/bin/cherenkov --version`

**Session A specific:**
- [ ] Ollama daemon running: `ollama serve` (in a background terminal)
- [ ] Ollama model pulled: `ollama list | grep qwen2.5`
- [ ] Target API healthy: `curl -sf http://localhost:8000/health || uvicorn target.target_api:app --port 8000 &`
- [ ] petstore.json present (or network available for curl download)

**Session B specific:**
- [ ] Docker Desktop running: `docker ps` (should return without error)
- [ ] Prism image pulled: `docker pull stoplight/prism:5`
- [ ] stripe_spec.json present: `ls /home/moaid/cherenkov-qa/stripe_spec.json`
- [ ] Target API running in regression mode: `REGRESSION_MODE=true uvicorn target.target_api:app &`

**Session C specific:**
- [ ] PITCH_DECK.html open in Chrome (Ctrl+L → open file)
- [ ] Chrome in full-screen mode: F11
- [ ] Slide 1 showing (press Home key or navigate to start)
- [ ] Speaker notes printed or on second monitor (press N key to toggle)

---

## Chapter 3: Recording Session A — Zero to Hero (10 min)

### Setup

```bash
# Open a clean WSL terminal, then:
cd /tmp && rm -rf cherenkov_demo_session_a
mkdir cherenkov_demo_session_a && cd cherenkov_demo_session_a
```

### Recording Workflow

**Step 1:** Open Loom → Screen + Audio → select Windows Terminal window → click Start Recording
**Step 2:** Wait 3 seconds (Loom shows countdown: 3…2…1…GO). Begin speaking intro.

**Step-by-step pacing (total: ~10 minutes):**

| Timestamp | Action | Verbal |
|-----------|--------|--------|
| 00:00–00:30 | Show blank terminal | "Let's start from scratch — a clean directory." |
| 00:30–01:30 | `cherenkov init` | Explain what cherenkov.toml does |
| 01:30–02:30 | `curl -o petstore.json ...` | "This is the real public Petstore OpenAPI spec" |
| 02:30–05:30 | `cherenkov generate --spec petstore.json` | Let LLM inference run — keep talking about the gates |
| 05:30–07:00 | Show generated `.spec.ts` file | Open with `cat tests/get_pet_by_id.spec.ts` |
| 07:00–09:30 | `cherenkov validate --target ...` | "Watch for the red lines" |
| 09:30–10:00 | Show summary + close | "Four real conformance bugs. One command." |

**If LLM inference takes too long (>120s):** Keep narrating: *"The local model is generating — this is running entirely on your machine, no API keys, no cloud."* The wait actually demonstrates the local-first value.

**Recovery from mistakes:**
- Typo in a command: just retype — don't apologise, viewers expect terminal typos
- Wrong directory: `cd` back and continue — edit out in Loom's trim tool after
- API timeout: say *"Let me restart that"* and rerun — keep energy up

**Recommended takes:** 2–3 dry runs before the keeper take. Time yourself on dry run 1.

**After recording:**
1. In Loom: click "Trim" → trim first 2 seconds and last 5 seconds (dead air)
2. Add chapters: 00:00 Install, 02:30 Generate, 07:00 Validate
3. Copy shareable link

---

## Chapter 4: Recording Session B — Live Case (15 min)

### Layout Setup

Use a split-screen layout:
- **Left 60%:** Windows Terminal (WSL2) — cherenkov commands
- **Right 40%:** Chrome — CHERENKOV Dashboard (`cherenkov dashboard` → localhost:8888) or Prism logs

In Loom, select "Full screen" recording mode to capture both panels.

### Recording Workflow

| Timestamp | Action |
|-----------|--------|
| 00:00–01:00 | Intro: "We're testing a real Stripe API subset using a local Prism mock" |
| 01:00–03:00 | Start Prism: `docker run -d -p 4010:4010 stoplight/prism:5 mock /path/to/stripe_spec.json` |
| 03:00–06:00 | `cherenkov generate --spec stripe_spec.json --repair` — explain the repair loop |
| 06:00–08:00 | Show Gate 6 failure + self-healing output |
| 08:00–10:00 | `cherenkov validate --target http://localhost:4010` — show the 422 vs 400 bug |
| 10:00–12:00 | `cherenkov hitl list` → `hitl show <id>` → `hitl approve <id>` |
| 12:00–14:00 | `cherenkov eject --output ./ejected_suite` — show the clean output |
| 14:00–15:00 | `cd ejected_suite && npx playwright test` — it still runs without CHERENKOV |

### Using Loom's Drawing Tools

During the validation output (timestamp ~08:00):
- Click the pen icon in the Loom recording bar
- Circle the "Expected: 422 / Got: 400" line in red
- Say: *"This is the bug — the server is returning 400 instead of the spec-required 422"*

### Common Mistakes to Avoid

⚠️ **Forgetting to start Docker:** Run `docker ps` before you record. If Docker isn't running, the Prism container command will fail immediately on camera.

⚠️ **HITL ID changes between takes:** Always run `cherenkov hitl list` at the start of the HITL segment to get the live ID. Never hardcode an ID in your notes — it changes every run.

⚠️ **LLM API timeout during `--repair` loop:** If the repair loop times out on camera, say: *"In a real run, this completes in under 30 seconds. Let me show you the expected output."* Then open a pre-run terminal with the output already visible.

---

## Chapter 5: Recording Session C — Executive Pitch (5 min)

### Slide Deck Setup

```bash
# Open the interactive HTML pitch deck in Chrome
# On Windows:
start chrome "\\wsl.localhost\Ubuntu-24.04\home\moaid\teamwork_projects\cherenkov_onboarding\PITCH_DECK.html"
```

1. Press **F11** to enter full-screen mode in Chrome
2. Press **N** to check speaker notes (toggle off before recording)
3. Navigate to Slide 1 with **Home** key or **←** arrow

### Keyboard Shortcuts During Recording

| Key | Action |
|-----|--------|
| `→` / `Space` | Next slide |
| `←` | Previous slide |
| `N` | Toggle speaker notes (keep OFF during recording) |
| `F` | Fullscreen |

### Voice Pacing Guide

5-minute session = ~1 minute per slide = ~120–150 words per slide.

| Slide | Target Duration | Opening line |
|-------|----------------|--------------|
| 1 — The Problem | 45s | "Let me start with an uncomfortable truth about AI-generated tests..." |
| 2 — The Principle | 45s | "CHERENKOV is built on one invariant: the spec is the law." |
| 3 — The Pipeline | 45s | "Every generated test passes through six deterministic gates." |
| 4 — Live Demo | 60s | "Here's what zero to hero actually looks like..." |
| 5 — Real Bug Caught | 60s | "These are real bugs from a real public API." |
| 6 — Self-Healing | 30s | "When the AI gets it wrong, CHERENKOV fixes it." |
| 7 — Anti Lock-In | 30s | "The eject command is the trust-builder." |
| 8 — QA Gate | 30s | "Four of five senior QA practitioners said yes." |
| 9 — CI/CD | 15s | "Five lines of YAML to integrate." |
| 10 — CTA | 30s | "You can run cherenkov init in the next 60 seconds." |

### Voice-Over Only Recording

If you want to record narration separately from the slide recording:
1. Record the slide clicks (no audio) using Loom with mic muted
2. Record audio-only in Audacity
3. Sync in DaVinci Resolve (free) or use Loom's video editor to replace audio

---

## Chapter 6: Audio Quality

### Recommended Microphone Setup

| Option | Quality | Cost | Notes |
|--------|---------|------|-------|
| **USB condenser mic** (e.g., Blue Yeti Nano, Rode NT-USB Mini) | ⭐⭐⭐⭐ | £80–£120 | Best for desk recordings |
| **Headset with boom mic** (e.g., Jabra Evolve2) | ⭐⭐⭐ | £60–£100 | Good for quick recordings |
| **Built-in laptop mic** | ⭐⭐ | Free | Acceptable for internal KT only |
| **Apple EarPods mic** | ⭐⭐⭐ | £20 | Surprisingly good, portable |

### Room Acoustics Tips

- Record in a **small room** with soft furnishings (bedroom > open office)
- Hang a **blanket behind you** if you get room echo
- Close windows and doors — HVAC and traffic noise ruin recordings
- Record at **off-peak hours** (early morning) for quietest background

### Loom Audio Settings

1. Loom settings → Microphone → select your USB mic (not "Default")
2. Enable **Noise Suppression** toggle
3. Test with the 30-second test: record a sentence, play back, check for hiss or echo

### 30-Second Audio Test

Before every recording session:
```
1. Start a Loom recording (Screen + Audio)
2. Say: "Testing, one two three. CHERENKOV QA demo audio check."
3. Stop recording
4. Play back at 100% volume
5. Check: no clipping (red peaks), no hiss, voice is clear and centred
6. Adjust mic volume if needed (Windows → Sound → Recording → mic properties)
```

### Post-Processing with Audacity (if needed)

```
1. Export Loom recording audio via Loom (Settings → Export)
2. Open .mp4 in Audacity (File → Import → Audio)
3. Select 2 seconds of silence (room noise only)
4. Effect → Noise Reduction → Get Noise Profile
5. Select all audio (Ctrl+A)
6. Effect → Noise Reduction → OK
7. Export as WAV, re-combine with video in DaVinci Resolve
```

---

## Chapter 7: asciinema Terminal Recordings

### Install

```bash
# On Ubuntu/WSL
pip install asciinema
# OR
sudo apt install asciinema

# Verify
asciinema --version  # should show 2.x
```

### Record Session A

```bash
# Navigate to the demo directory
cd /tmp && mkdir -p cherenkov_session_a && cd cherenkov_session_a

# Start asciinema recording
asciinema rec \
  -t "CHERENKOV QA: Zero to Hero" \
  ~/RECORDING_ASSETS/casts/session_a.cast \
  --overwrite \
  --idle-time-limit 2.5

# The terminal is now recording — run the pre-built cast script:
bash ~/teamwork_projects/cherenkov_onboarding/casts/cast_session_a.sh

# Press Ctrl+D when done
```

### Record Session B

```bash
asciinema rec \
  -t "CHERENKOV QA: Live Case — HITL + Repair" \
  ~/RECORDING_ASSETS/casts/session_b.cast \
  --overwrite \
  --idle-time-limit 2.5

bash ~/teamwork_projects/cherenkov_onboarding/casts/cast_session_b.sh

# Press Ctrl+D when done
```

### Preview Your Recording

```bash
asciinema play ~/RECORDING_ASSETS/casts/session_a.cast
asciinema play --speed=1.5 ~/RECORDING_ASSETS/casts/session_a.cast  # 1.5x speed
```

### Upload to asciinema.org

```bash
# Creates a permanent shareable URL
asciinema upload ~/RECORDING_ASSETS/casts/session_a.cast
# Output: https://asciinema.org/a/XXXXXXX
```

### Embed in README

```markdown
[![CHERENKOV Zero to Hero](https://asciinema.org/a/XXXXXXX.svg)](https://asciinema.org/a/XXXXXXX)
```

### Convert to GIF

```bash
# Install agg (asciinema GIF generator — requires Rust)
cargo install agg
# OR download binary from https://github.com/asciinema/agg/releases

# Convert to GIF (optimised for README embed: 100 cols wide, 1.5x speed)
agg \
  --speed 1.5 \
  --cols 100 \
  --rows 28 \
  --font-size 14 \
  ~/RECORDING_ASSETS/casts/session_a.cast \
  ~/RECORDING_ASSETS/gifs/session_a.gif

# View the GIF
xdg-open ~/RECORDING_ASSETS/gifs/session_a.gif
```

### Adjust Playback Speed

```bash
# The --idle-time-limit flag caps silence gaps during recording
# The --speed flag during playback speeds up the whole thing
asciinema play --speed=2.0 session_a.cast  # 2x — good for fast previews
asciinema play --speed=0.8 session_a.cast  # 0.8x — for slow, educational viewing
```

---

## Chapter 8: Publishing & Embedding

### Loom

1. After recording: click "Share" → copy link
2. Set privacy: **"Anyone with the link"** for external pitch sessions, **"Team"** for internal KT
3. Add password for sensitive demos
4. **Add chapters:** in the Loom editor, click the timeline → "+ Chapter" at key timestamps:
   - 00:00 — Install
   - 02:30 — Generate
   - 07:00 — Validate
5. Download as MP4: Loom menu → "Download" (requires paid plan or use OBS)

### YouTube (Unlisted)

For long-term embedding and SEO:
1. Upload to YouTube as **Unlisted** (not Public — keeps it undiscoverable but embeddable)
2. Add chapters in the description:
   ```
   00:00 Introduction
   00:30 cherenkov init
   02:30 Generate tests with local LLM
   07:00 Validate against Petstore API
   09:30 Review conformance failures
   ```
3. Add a custom thumbnail (see thumbnail design spec in `RECORDING_ASSETS/README.md`)

### GitHub README Embed

**Option A — Animated GIF (recommended for small clips):**
```markdown
![CHERENKOV Zero to Hero](../recordings/session_a.gif)
```

**Option B — YouTube thumbnail linking to video:**
```markdown
[![CHERENKOV Zero to Hero](https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg)](https://youtu.be/VIDEO_ID)
```

**Option C — asciinema badge:**
```markdown
[![asciicast](https://asciinema.org/a/XXXXXXX.svg)](https://asciinema.org/a/XXXXXXX)
```

### Notion / Confluence

- **Notion:** Paste the Loom URL directly into a Notion block → Loom player embeds automatically
- **Confluence:** Insert → Multimedia → paste Loom/YouTube URL

### docs-site Embed

Add to `docs-site/index.html`:
```html
<section id="demo">
  <h2>See It In Action</h2>
  <!-- Loom embed -->
  <div style="position:relative;padding-bottom:56.25%;height:0;">
    <iframe src="https://www.loom.com/embed/YOUR_LOOM_ID"
      style="position:absolute;top:0;left:0;width:100%;height:100%;"
      frameborder="0" allowfullscreen></iframe>
  </div>
  <!-- Or YouTube embed -->
  <iframe width="100%" height="450"
    src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
    frameborder="0" allowfullscreen></iframe>
</section>
```

### File Naming Convention

| Asset | Naming Pattern | Example |
|-------|----------------|---------|
| MP4 video | `cherenkov_{session}_{topic}_v{N}.mp4` | `cherenkov_session_a_zero_to_hero_v1.mp4` |
| asciinema cast | `session_{letter}.cast` | `session_a.cast` |
| Animated GIF | `session_{letter}.gif` | `session_a.gif` |
| Thumbnail | `thumb_session_{letter}.png` | `thumb_session_a.png` |

---

## Chapter 9: Quick Reference Card

| Session | Tool | Duration | Audience | Key Pre-flight Steps | Output File |
|---------|------|----------|----------|---------------------|-------------|
| **A — Zero to Hero** | asciinema + Loom | 10 min | Developers | Ollama running · Petstore spec downloadable · Target API healthy | `session_a_zero_to_hero_v1.mp4` |
| **B — Live Case** | Loom (split-screen) | 15 min | QA Leads / SDETs | Docker running · Prism image pulled · stripe_spec.json present · Target API in regression mode | `session_b_live_case_v1.mp4` |
| **C — Executive Pitch** | Loom (slide narration) | 5 min | Executives | PITCH_DECK.html in Chrome full-screen · speaker notes printed | `session_c_executive_pitch_v1.mp4` |

---

## Appendix: Useful Commands Reference

```bash
# Start Target API (normal mode)
cd /home/moaid/cherenkov-qa
source .venv/bin/activate
uvicorn target.target_api:app --host 127.0.0.1 --port 8000 &

# Start Target API (regression/bug mode)
REGRESSION_MODE=true uvicorn target.target_api:app --host 127.0.0.1 --port 8000 &

# Start Prism mock for Stripe
docker run -d --name prism_demo -p 4010:4010 \
  -v /home/moaid/cherenkov-qa:/api \
  stoplight/prism:5 mock -h 0.0.0.0 /api/stripe_spec.json

# Start Ollama (local LLM server)
ollama serve &
ollama pull qwen2.5-coder:7b  # only needed once

# asciinema recording
asciinema rec -t "CHERENKOV Demo" demo.cast --idle-time-limit 2.5

# Kill all background demo processes
pkill -f uvicorn; docker rm -f prism_demo; pkill -f ollama

# Full demo harness (runs all phases automatically)
bash ~/teamwork_projects/cherenkov_onboarding/run_demo.sh
```
