# RECORDING_ASSETS — Directory Guide

> **Purpose:** Central storage for all recorded demo assets: terminal screencasts (`.cast`),
> screen recordings (`.mp4`), animated GIFs (`.gif`), and thumbnail images (`.png`).
> These assets are consumed by the session guides, the pitch deck, and the KT onboarding package.

---

## Directory Layout

```
RECORDING_ASSETS/
├── README.md                    ← you are here
│
├── casts/                       ← asciinema terminal recordings
│   ├── session_a_zero_to_hero.cast
│   ├── session_b_hitl_eject.cast
│   └── session_c_pitch_companion.cast
│
├── mp4/                         ← screen-captured video recordings
│   ├── session_a_zero_to_hero.mp4
│   ├── session_b_hitl_eject.mp4
│   ├── session_c_pitch_companion.mp4
│   ├── run_demo_full.mp4        ← full run_demo.sh recording
│   └── dashboard_walkthrough.mp4
│
├── gif/                         ← animated GIFs (for README embeds, Slack previews)
│   ├── cherenkov_green_pass.gif  ← Phase 1 green run loop
│   ├── cherenkov_red_fail.gif    ← Phase 2 regression detection
│   ├── cherenkov_eject.gif       ← eject command walkthrough
│   └── cherenkov_hitl.gif        ← HITL queue review walkthrough
│
└── thumbnails/                  ← PNG thumbnails for video links
    ├── session_a_thumb.png       ← 1280×720 thumbnail for Session A
    ├── session_b_thumb.png       ← 1280×720 thumbnail for Session B
    ├── session_c_thumb.png       ← 1280×720 thumbnail for Session C
    └── demo_harness_thumb.png    ← 1280×720 thumbnail for run_demo.sh
```

---

## How to Record

### Terminal Screencasts (asciinema)

```bash
# Install asciinema
pip install asciinema        # or: brew install asciinema

# Record Session A
asciinema rec \
  -t "CHERENKOV: Zero to Hero" \
  --overwrite \
  RECORDING_ASSETS/casts/session_a_zero_to_hero.cast \
  --command "bash casts/cast_session_a.sh"

# Record Session B
asciinema rec \
  -t "CHERENKOV: HITL + Eject" \
  --overwrite \
  RECORDING_ASSETS/casts/session_b_hitl_eject.cast \
  --command "bash casts/cast_session_b.sh"
```

> **Tip:** Set your terminal to 220×50 characters before recording for the best playback experience.
> ```bash
> printf '\e[8;50;220t'
> ```

### Screen Recordings (mp4)

Use any screen recorder (OBS, QuickTime, Kazam, or `ffmpeg` + `x11grab`):

```bash
# Linux/ffmpeg example (adjust display, resolution, and output path)
ffmpeg -video_size 1920x1080 -framerate 30 \
  -f x11grab -i :0.0 \
  RECORDING_ASSETS/mp4/session_a_zero_to_hero.mp4
```

Or, on macOS with QuickTime: File → New Screen Recording → select window → save to `mp4/`.

### GIFs from MP4

```bash
# Convert a segment of an MP4 to a looping GIF (requires ffmpeg + gifsicle)
ffmpeg -i RECORDING_ASSETS/mp4/session_a_zero_to_hero.mp4 \
  -vf "fps=15,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  -loop 0 \
  RECORDING_ASSETS/gif/cherenkov_green_pass.gif
```

### Playing Back asciinema Casts

```bash
# Local playback
asciinema play RECORDING_ASSETS/casts/session_a_zero_to_hero.cast

# Upload to asciinema.org (optional, for sharing links)
asciinema upload RECORDING_ASSETS/casts/session_a_zero_to_hero.cast
```

---

## Naming Conventions

| Asset type | Pattern | Example |
|---|---|---|
| asciinema cast | `session_<id>_<slug>.cast` | `session_a_zero_to_hero.cast` |
| mp4 recording | `session_<id>_<slug>.mp4` | `session_b_hitl_eject.mp4` |
| animated GIF | `cherenkov_<feature>.gif` | `cherenkov_green_pass.gif` |
| thumbnail | `<slug>_thumb.png` | `session_a_thumb.png` |

**Rules:**
- Use `snake_case` for all filenames.
- Prefix session recordings with `session_<a|b|c>_`.
- Thumbnails must be exactly **1280×720 px** PNG.
- GIFs target **960 px wide**, max **5 MB** (for GitHub README embedding).
- No spaces in filenames.

---

## Placeholder Thumbnails

The following placeholder thumbnails describe what each image should contain when produced:

| File | Description |
|------|-------------|
| `thumbnails/session_a_thumb.png` | Dark terminal background with CHERENKOV ASCII banner and a green `✓ CONFORMANT` badge. Text: *"Zero to Hero: 5 min quickstart"*. |
| `thumbnails/session_b_thumb.png` | Split-screen: left shows HITL queue list; right shows ejected test file in editor. Text: *"HITL + Eject: advanced workflow"*. |
| `thumbnails/session_c_thumb.png` | Slide-style image with CHERENKOV logo, ROI chart, and text: *"Pitch Companion: present to leadership"*. |
| `thumbnails/demo_harness_thumb.png` | Terminal showing Phase 1 green banner and Phase 2 red banner side by side. Text: *"Live Demo Harness: run_demo.sh"*. |

---

## Embedding in Docs

Once assets exist, embed them in session guides and the pitch deck using:

```markdown
<!-- asciinema cast (requires asciinema player JS) -->
<asciinema-player src="RECORDING_ASSETS/casts/session_a_zero_to_hero.cast" cols="220" rows="50"></asciinema-player>

<!-- Animated GIF (GitHub README / Markdown) -->
![CHERENKOV green pass demo](RECORDING_ASSETS/gif/cherenkov_green_pass.gif)

<!-- Linked thumbnail to video -->
[![Session A Thumbnail](RECORDING_ASSETS/thumbnails/session_a_thumb.png)](RECORDING_ASSETS/mp4/session_a_zero_to_hero.mp4)
```

---

## Asset Status

| Asset | Status | Notes |
|-------|--------|-------|
| `casts/session_a_zero_to_hero.cast` | 🔲 Pending | Record with `cast_session_a.sh` |
| `casts/session_b_hitl_eject.cast` | 🔲 Pending | Record with `cast_session_b.sh` |
| `casts/session_c_pitch_companion.cast` | 🔲 Pending | Record with session C script |
| `mp4/session_a_zero_to_hero.mp4` | 🔲 Pending | Screen recording |
| `mp4/session_b_hitl_eject.mp4` | 🔲 Pending | Screen recording |
| `mp4/run_demo_full.mp4` | 🔲 Pending | Record `run_demo.sh` live run |
| `gif/cherenkov_green_pass.gif` | 🔲 Pending | Convert from mp4 |
| `gif/cherenkov_red_fail.gif` | 🔲 Pending | Convert from mp4 |
| `thumbnails/session_a_thumb.png` | 🔲 Pending | Design per spec above |
| `thumbnails/session_b_thumb.png` | 🔲 Pending | Design per spec above |
| `thumbnails/session_c_thumb.png` | 🔲 Pending | Design per spec above |
| `thumbnails/demo_harness_thumb.png` | 🔲 Pending | Design per spec above |

Update this table to ✅ Done as assets are produced.

---

*See also: [VIDEO_RECORDING_GUIDE.md](../VIDEO_RECORDING_GUIDE.md) for the full recording workflow including toolchain setup, post-processing checklist, and upload targets.*
