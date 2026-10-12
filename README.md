# ⌨️ ClackLab

**Your keyboard types. ClackLab gives it a personality.**

Ever typed an entire essay in silence and felt like something was missing? We did too.

ClackLab is a macOS application designed to bring the satisfying sounds of mechanical keyboards to your everyday typing experience. Whether you're a fan of crisp clicks, deep thocks, or smooth, subtle taps, ClackLab aims to make every keystroke sound a little more satisfying.

### ✨ What's the clack about?

- 🔊 **Mechanical sound profiles** — Find the sound that matches your typing vibe.
- ⚡ **Low-latency playback** — Keep the sounds snappy without turning your typing into a percussion concert.
- 🎛️ **Customizable experience** — Tune your keyboard's personality to your liking.
- 🍎 **Made for macOS** — Designed to fit into your Mac workflow.
- 🔒 **Privacy-minded design** — Keyboard sounds, not keyboard surveillance. Your typed content shouldn't need to leave your machine.

**The mission:** Make typing more enjoyable, one *clack* at a time.

Because productivity is important. But sounding like a tiny mechanical orchestra? Also important.

---

## 🛠️ Highlights & Core Features

- **Ultra-Low Latency Audio Pipeline**: Preinitialized continuous PortAudio output stream running at 48,000 Hz with a 128-frame buffer (2.67 ms hardware buffer period).
- **In-Memory Preloaded Samples**: Audio waveforms are pre-resampled into contiguous 32-bit float stereo arrays in RAM. Zero disk reads, zero decoding, and zero network calls during typing.
- **Listen-Only macOS Global Keyboard Monitor**: Uses native Quartz `CGEventTap` with `kCGEventTapOptionListenOnly`. Does **not** intercept, suppress, or modify keystrokes; normal typing in all applications is completely untouched.
- **Natural Acoustic Realism**:
  - 5 round-robin variations per profile with anti-repetition memory (avoids identical immediate repeats).
  - Key-down sounds and optional Key-up release sounds.
  - Dedicated stabilizer sounds for Spacebar, Enter, and Backspace.
  - Optional subtle micro-pitch variation (simulates natural finger velocity dynamics).
  - Bounded 32-voice mixer with soft-limiting saturation (prevents harsh digital clipping on rapid chords).
- **6 Authentic Switch Profiles Out of the Box**:
  - **Tactile**: Holy Panda (prominent rounded bump, snappy clack)
  - **Linear**: Cherry MX Black (smooth slider travel, clean bottom-out)
  - **Clicky**: Cherry MX Blue (crisp click-leaf actuation)
  - **Silent**: Cherry MX Silent (silicone pad cushioned travel, muted highs)
  - **Thocky**: Boba U4T (deep cavity resonance, rich PBT bottom-out)
  - **Creamy**: NovelKeys Cream (silky-smooth rounded marbly acoustics)
- **macOS Taskbar / Menu Bar Keyboard Quick Access (⌨️)**: Native menu bar status item provides immediate access to all Dashboard controls from anywhere on your Mac:
  - Quick master enable/disable mute toggle
  - Instant switch profile switching (Tactile, Linear, Clicky, Silent, Thocky, Creamy)
  - Master volume presets (100%, 85%, 70%, 50%, 25%, Mute)
  - Instant keystroke sound preview
  - Audio engine & Accessibility permission health indicators
  - Click to show/restore the dashboard window
  - Closing the main window hides to the menu bar so typing sounds continue seamlessly in the background
- **100% Private & Offline**: Zero internet connections required, zero keystroke logging, zero text inspection, and zero microphone access.
- **Monotonic Latency Diagnostics**: Live telemetry measuring median (p50), 95th percentile (p95), max delay, active polyphony, and underruns.

---

## 📂 Project Architecture

```
ClackLab/
├── main.py                     # Entry point & CLI benchmark runner
├── pyproject.toml              # Build config & test settings
├── requirements.txt            # Pinned dependencies
├── LICENSES.md                 # Software & audio asset MIT licenses
├── README.md                   # Complete documentation
│
├── app/
│   ├── models.py               # Domain models, event classes, profiles
│   ├── settings.py             # Persistent settings manager (~/Library/Application Support/ClackLab)
│   ├── application.py          # Master application coordinator
│   │
│   ├── audio/
│   │   ├── audio_engine.py     # PortAudio callback stream & bounded 32-voice mixer
│   │   ├── sample_library.py   # RAM sample caching, anti-repetition, pitch jitter
│   │   ├── sample_player.py    # High-level playback coordinator
│   │   ├── audio_devices.py    # Output device enumeration & discovery
│   │   └── latency_metrics.py  # Monotonic nanosecond latency telemetry
│   │
│   ├── keyboard/
│   │   ├── event_monitor.py    # Quartz CGEventTap daemon thread (ListenOnly)
│   │   ├── event_filter.py     # Keycode classification & repeat suppression
│   │   └── permission_manager.py# macOS Accessibility trust verification
│   │
│   ├── profiles/
│   │   ├── switch_profiles.py  # Switch acoustic definitions
│   │   └── profile_manager.py  # Profile discovery & manifest loader
│   │
│   ├── soundpacks/
│   │   ├── pack_validator.py   # Audio header & schema validator
│   │   └── pack_manager.py     # Pack folder & ZIP archive importer
│   │
│   ├── system/
│   │   └── login_item.py       # macOS Launch at Login via LaunchAgents
│   │
│   └── ui/
│       ├── styles.py           # Premium dark & light mechanical keyboard QSS
│       ├── main_window.py      # QMainWindow with multi-tab layout & local preview
│       ├── tray_icon.py        # macOS menu bar / taskbar keyboard status icon & quick menu
│       ├── dashboard.py        # Master switch, live pills, volume, quick profile
│       ├── keyboard_view.py    # Visual 60% Mac keyboard with keycap animations
│       ├── switch_library.py   # Rich cards for all 6 switch profiles
│       ├── sound_settings.py   # Volume, pitch jitter, and key behavior toggles
│       ├── audio_devices_view.py# Target output device & buffer size selector
│       ├── soundpacks_view.py  # Custom sound pack importer & inspector
│       ├── permissions_view.py # macOS Accessibility onboarding & privacy pledge
│       └── diagnostics_view.py # Live latency telemetry & typing benchmark
│
├── assets/
│   ├── icon.icns               # macOS Application Icon Bundle
│   ├── icon_keyboard.png       # Menu bar keyboard symbol
│   ├── logo.png                # Modern mechanical keycap logo
│   └── sounds/                 # 48kHz WAV audio profiles (Linear, Tactile, Clicky, Silent, Thocky, Creamy)
│       ├── manifest.json
│       ├── linear/
│       ├── tactile/
│       ├── clicky/
│       ├── silent/
│       ├── thocky/
│       └── creamy/
│
├── tests/                      # Automated pytest suite (44 tests)
│   ├── test_audio_mixer.py
│   ├── test_event_filter.py
│   ├── test_interactive_keys.py
│   ├── test_latency_metrics.py
│   ├── test_login_item.py
│   ├── test_pack_validation.py
│   ├── test_profiles.py
│   ├── test_sample_library.py
│   ├── test_settings.py
│   ├── test_tray_icon.py
│   └── test_virtual_typing.py
│
└── scripts/
    ├── run_dev.sh              # One-command development runner
    ├── build_app.sh            # PyInstaller macOS .app bundle builder
    └── prepare_sound_assets.py # Sample processing & normalization script
```

---

## 🚀 Getting Started

### Prerequisites
- macOS 12 Monterey, macOS 13 Ventura, macOS 14 Sonoma, macOS 15 Sequoia, or newer.
- Python 3.10+ (Apple Silicon arm64 or Intel x86_64).

### 1. Quick Launch
Run the provided development launcher:
```bash
./scripts/run_dev.sh
```

Or manually:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### 2. Granting macOS Permissions
To listen to keystrokes while typing in other apps:
1. Open **System Settings > Privacy & Security > Accessibility**.
2. Enable your Terminal (or `ClackLab.app`).
3. Return to ClackLab and click **Verify Permission Now** in the **Permissions & Privacy** tab.

*Note: ClackLab includes a **Local Typing Preview Mode**. When the ClackLab window has focus, you can type in the Live Typing Playground or click virtual keycaps to test switches immediately without granting background system permissions.*

---

## ⚡ Latency Benchmark & Diagnostics

ClackLab includes a headless command-line benchmarking mode that stress-tests the PortAudio engine and measures real scheduling latency:

```bash
python3 main.py --benchmark --profile thocky
```

Example measured performance on macOS Apple Silicon:
```
============================================================
CLACKLAB CLI BENCHMARK & AUDIO ENGINE TEST
============================================================
macOS Accessibility Trusted: True
Default Output Device: MacBook Pro Speakers
Discovered 6 switch profiles: ['creamy', 'tactile', 'thocky', 'linear', 'silent', 'clicky']
Testing Switch Profile: Boba U4T (Thocky) (thocky)
Audio engine started: SR=48000Hz, BlockSize=128 (2.67ms latency)

Streaming active. Simulating rapid mechanical typing...
============================================================
BENCHMARK RESULTS:
  Total Keystrokes Measured : 100
  Median Latency (p50)      : 0.227 ms
  95th Percentile (p95)     : 0.353 ms
  Maximum Latency           : 0.404 ms
  Buffer Underruns          : 0
  Configured Buffer Period  : 2.67 ms
============================================================
```

---

## 🧪 Running the Automated Test Suite

Run all 44 unit and integration tests with `pytest`:
```bash
pytest -v
```

Tests cover:
- Audio mixer bounded polyphony & soft limiting
- Keyboard keycode classification & repeat suppression
- Nanosecond latency tracking & percentile calculations
- Sound pack validation & corruption handling
- Switch profile discovery & manifest completeness
- Preloaded sample caching & anti-repetition selection
- Persistent settings JSON serialization & corruption recovery
- Launch at Login LaunchAgent creation and removal
- Menu bar status item actions and toggles
- Interactive virtual typing and playground input handling

---

## 📦 Building a Standalone macOS App Bundle (.app)

To package ClackLab into a distributable `ClackLab.app` bundle:
```bash
./scripts/build_app.sh
```
The resulting application is placed in `dist/ClackLab.app`.

---

## 🔒 Privacy Policy & Safety Guarantee

- **Zero Logging**: ClackLab does not store, transmit, or analyze text typed by the user. Keystroke events are discarded immediately after selecting an acoustic sample.
- **Listen-Only Tap**: The keyboard monitor operates strictly in `kCGEventTapOptionListenOnly` mode. It is physically incapable of suppressing, modifying, or delaying keyboard input.
- **No Microphone Access**: Sound generation is pure output; input audio devices are never opened or recorded.
- **Local Operation**: The software functions 100% offline.

---

## 📄 License
MIT License. See [LICENSES.md](LICENSES.md) for full application and audio sample attributions.
