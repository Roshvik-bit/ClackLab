# ClackLab

<div align="center">

**Ultra-Low-Latency Virtual Mechanical Keyboard Sound Engine for macOS and Windows**

[![macOS](https://img.shields.io/badge/macOS-12%20%7C%2013%20%7C%2014%20%7C%2015-blue.svg?logo=apple&logoColor=white)](https://github.com/Roshvik-bit/ClackLab)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt%206)-41CD52.svg?logo=qt&logoColor=white)](https://www.qt.io/)
[![PortAudio](https://img.shields.io/badge/Audio-PortAudio%20%40%2048kHz-FF6F00.svg)](http://www.portaudio.com/)
[![Tests](https://img.shields.io/badge/tests-47%20passed-brightgreen.svg?logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSES.md)

*High-performance mechanical keyboard acoustic simulation engine for desktop operating systems.*

[Overview](#overview) • [Downloads](#downloads-and-releases) • [Features](#core-features) • [Installation](#installation-and-permissions) • [Switch Profiles](#acoustic-switch-profiles) • [Menu Bar & Dock](#menu-bar-and-dock-integration) • [Architecture](#project-architecture) • [Development](#development-guide)

</div>

---

## Overview

ClackLab is a specialized, ultra-low-latency acoustic simulation engine engineered to reproduce realistic mechanical keyboard acoustics globally across all desktop applications.

Operating entirely offline with zero keystroke logging, ClackLab leverages native operating system event hooks in listen-only mode. Keystrokes are mapped to acoustic sound profiles, and preloaded studio-grade audio waveforms are scheduled directly into a continuous 48,000 Hz real-time PortAudio ring buffer, achieving consistent sub-millisecond scheduling latencies.

The system is designed for minimal resource consumption, deterministic execution, and native macOS desktop integration, including status bar operation and configurable Dock visibility.

---

## Downloads and Releases

| Platform | Package Format | Direct Download | Architecture |
| :--- | :--- | :--- | :--- |
| macOS | Disk Image (`.dmg`) | [ClackLab-v1.0.0-macOS.dmg](dist/ClackLab-v1.0.0-macOS.dmg) | Universal / Apple Silicon (M1/M2/M3/M4) and Intel x86_64 |
| Windows | Executable (`.exe`) | [ClackLab-v1.0.0-Windows.exe](https://github.com/Roshvik-bit/ClackLab/releases/download/v1.0.0-windows/ClackLab-v1.0.0-Windows.exe) | Windows 10 / 11 (64-bit) |

---

## Core Features

### Real-Time Audio Pipeline
- **Sub-Millisecond Scheduling**: Powered by a preinitialized continuous PortAudio stream running at 48,000 Hz with a 128-frame hardware buffer (2.67 ms buffer period). Measured median p50 scheduling latency is under 0.35 ms.
- **In-Memory Waveform Caching**: All audio samples are normalized and cached in memory as contiguous 32-bit floating-point NumPy arrays. No disk I/O, audio decoding, or memory allocations occur during active typing.
- **Dynamic 32-Voice Limiter**: Multi-channel voice mixer bounded to 32 simultaneous voices with soft-knee limiting to eliminate digital clipping during rapid burst typing.

### Acoustic Realism Engine
- **Round-Robin Variation**: 5 distinct acoustic sample recordings per switch category with anti-repetition state tracking to avoid identical sequential playback.
- **Independent Key Dynamics**: Separate volume attenuation and acoustic profiles for key-down actuation and key-up switch reset.
- **Dedicated Stabilizer Acoustics**: Independent heavier sample profiles specifically triggered for large stabilized keycaps (Spacebar, Return, Backspace).
- **Subtle Pitch Jitter**: Configurable Gaussian pitch variation simulating natural finger strike velocity differentials.

### Operating System Integration
- **Zero-Logging Privacy Model**: Native Quartz `CGEventTap` configured strictly in `kCGEventTapOptionListenOnly` mode. Keystrokes are consumed purely as hardware scan codes and immediately discarded without inspecting character values or recording input text.
- **Menu Bar Status Item**: Native status bar control for immediate profile selection, volume adjustment, engine pause/resume, and settings access.
- **Configurable Dock Visibility**: Runs as a standard application or as a native accessory utility (`NSApplicationActivationPolicyAccessory`), allowing users to remove the app from the macOS Dock while retaining full menu bar presence.
- **Modern Startup Management**: Integrated with macOS 13+ Ventura, Sonoma, and Sequoia `SMAppService` via PyObjC `ServiceManagement`, with backward compatibility for user LaunchAgents.

---

## Acoustic Switch Profiles

ClackLab includes 6 carefully curated, studio-recorded acoustic profiles:

| Profile Identifier | Physical Switch Equivalent | Acoustic Classification | Profile Description |
| :--- | :--- | :--- | :--- |
| `tactile` | Drop + Invyr Holy Panda | Tactile | Pronounced tactile bump with snappy clack and crisp switch return. |
| `thocky` | Gazzew Boba U4T | Thocky | Deep acoustic cavity resonance with low-frequency PBT bottom-out profile. |
| `creamy` | NovelKeys Cream | Creamy | Rounded polyoxymethylene (POM) housing travel with smooth acoustic signature. |
| `linear` | Cherry MX Black | Linear | Consistent linear slider travel with clean, uniform housing bottom-out. |
| `clicky` | Cherry MX Blue | Clicky | Crisp click-leaf mechanical actuation with bright high-frequency tactile report. |
| `silent` | Cherry MX Silent Red | Silent | Internal elastomer dampening pads for quiet, low-noise environments. |

---

## Installation and Permissions

### macOS Installation via DMG

1. Mount the disk image: [ClackLab-v1.0.0-macOS.dmg](dist/ClackLab-v1.0.0-macOS.dmg).
2. Drag `ClackLab.app` into the `/Applications` directory.
3. Launch ClackLab from `/Applications` or Spotlight.

```
+-------------------------------------------------------+
|  ClackLab Disk Image                                  |
|                                                       |
|       [ ClackLab.app ]  ------->  [ Applications ]    |
|                                                       |
+-------------------------------------------------------+
```

### macOS Gatekeeper Security Configuration

Because ClackLab is distributed as an open-source binary, macOS Gatekeeper may present a dialog stating that the developer cannot be verified or that the application was downloaded from the internet.

To authorize execution:
1. Open Terminal and remove the browser quarantine extended attribute:
   ```bash
   xattr -cr /Applications/ClackLab.app
   ```
2. Alternatively, open **System Settings > Privacy & Security**, navigate to **Security**, and click **Open Anyway**.

### macOS Accessibility Permission Setup

To monitor global keyboard scan codes outside the active ClackLab window:
1. Open **System Settings > Privacy & Security > Accessibility**.
2. Locate **ClackLab** (or your Terminal application during development) and toggle permission to ON.
3. The ClackLab status icon in the menu bar will update to active status (`Running`).

> **Local Preview Note:** If accessibility permissions are not yet granted, switch acoustic profiles can still be evaluated inside the ClackLab dashboard using the built-in typing playground and visual keyboard interface.

---

## Menu Bar and Dock Integration

ClackLab provides flexible desktop presentation modes tailored for background execution:

### Menu Bar Status Item
The menu bar status item provides persistent control without requiring foreground windows:
- Master sound pause and resume toggle.
- Switch profile selector across all installed acoustic sets.
- Volume stepping presets (100%, 85%, 70%, 50%, 25%, Mute).
- Acoustic test preview trigger.
- Direct navigation to Settings, Diagnostics, or Application Quit.

### Removing ClackLab from the macOS Dock
By default, ClackLab operates in accessory mode to keep desktop space unencumbered:
- **Hide from Dock**: Configure ClackLab to run exclusively from the top menu bar without taking up space in the macOS Dock.
- **Toggle Visibility**: 
  - Access the menu bar menu and toggle **Show in macOS Dock**.
  - Or configure via **Sound Settings > System & Background Operation > Show ClackLab Icon in macOS Dock**.
- **Window Management**: Closing the dashboard window with `Cmd + W` hides the graphical interface while audio synthesis continues seamlessly in the background.

---

## Project Architecture

```
ClackLab/
├── main.py                     # Entry point, CLI benchmark runner, single-instance lock
├── pyproject.toml              # Build metadata and package dependencies
├── requirements.txt            # Pinned dependency requirements
├── ClackLab.spec               # PyInstaller macOS application bundle specification
├── LICENSES.md                 # Software and audio sample license documentation
├── README.md                   # Technical system documentation
│
├── app/
│   ├── models.py               # Domain models, event representations, profile schemas
│   ├── settings.py             # Persistent JSON settings manager (~/Library/Application Support/ClackLab)
│   ├── application.py          # Master application lifecycle and system event coordinator
│   │
│   ├── audio/
│   │   ├── audio_engine.py     # Real-time continuous PortAudio callback and 32-voice limiter
│   │   ├── sample_library.py   # RAM sample caching, anti-repetition memory, pitch variation
│   │   ├── sample_player.py    # High-level acoustic playback coordinator
│   │   ├── audio_devices.py    # Output device enumeration and hardware discovery
│   │   └── latency_metrics.py  # Monotonic nanosecond latency telemetry and statistics
│   │
│   ├── keyboard/
│   │   ├── event_monitor.py    # Quartz CGEventTap daemon running on CFRunLoop (ListenOnly)
│   │   ├── event_filter.py     # Scan code classification and repeat event suppression
│   │   └── permission_manager.py# Native macOS Accessibility trust verification
│   │
│   ├── profiles/
│   │   ├── switch_profiles.py  # Switch acoustic profile definitions
│   │   └── profile_manager.py  # Profile discovery and manifest loading
│   │
│   ├── runtime/
│   │   ├── background_runtime.py# Threaded background runtime controller
│   │   └── runtime_state.py    # Runtime lifecycle state machine
│   │
│   ├── soundpacks/
│   │   ├── pack_validator.py   # Audio header and JSON schema validator
│   │   └── pack_manager.py     # Custom sound pack folder and archive importer
│   │
│   ├── system/
│   │   ├── dock_manager.py     # macOS NSApplication activation policy controller
│   │   ├── login_item.py       # Modern SMAppService and LaunchAgents login management
│   │   ├── single_instance.py  # Local socket IPC single-instance controller
│   │   └── diagnostics_logger.py# Structured lifecycle event file logger
│   │
│   └── ui/
│       ├── styles.py           # Dark and light mechanical keyboard QSS stylesheet themes
│       ├── main_window.py      # QMainWindow coordinator with multi-tab layout and local preview
│       ├── tray_icon.py        # Menu bar status item with quick access controls
│       ├── dashboard.py        # Primary dashboard view, status indicators, master toggles
│       ├── keyboard_view.py    # Graphical 60% layout keyboard with live keycap actuation
│       ├── switch_library.py   # Interactive card selector for switch acoustic profiles
│       ├── sound_settings.py   # Volume, pitch jitter, and behavior tuning controls
│       ├── audio_devices_view.py# Audio output target selector and buffer size configuration
│       ├── soundpacks_view.py  # Custom sound pack importer and metadata inspector
│       ├── permissions_view.py # macOS Accessibility onboarding and privacy verification
│       └── diagnostics_view.py # Live telemetry monitoring and benchmarking interface
│
├── assets/
│   ├── icon.icns               # macOS multi-resolution application icon bundle
│   ├── icon_keyboard.png       # Menu bar template symbol
│   ├── logo.png                # Primary application branding
│   └── sounds/                 # 48 kHz WAV audio assets across all bundled profiles
│       └── manifest.json
│
├── tests/                      # Automated pytest verification suite (47 unit and integration tests)
│   ├── test_audio_mixer.py
│   ├── test_dock_manager.py    # macOS Dock visibility and activation policy tests
│   ├── test_event_filter.py
│   ├── test_interactive_keys.py
│   ├── test_latency_metrics.py
│   ├── test_login_item.py      # ServiceManagement and LaunchAgents integration tests
│   ├── test_pack_validation.py
│   ├── test_profiles.py
│   ├── test_sample_library.py
│   ├── test_settings.py
│   ├── test_tray_icon.py
│   └── test_virtual_typing.py
│
└── scripts/
    ├── run_dev.sh              # Development environment runner
    ├── build_app.sh            # PyInstaller application bundle compiler
    ├── build_dmg.sh            # Compressed macOS DMG package generator
    └── prepare_sound_assets.py # Audio asset ingestion and normalization script
```

---

## Development Guide

### Prerequisites
- macOS 12 Monterey or newer (tested through macOS 15 Sequoia).
- Python 3.10, 3.11, or 3.12 (Apple Silicon or Intel).
- PortAudio development libraries.

### 1. Environment Configuration

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/Roshvik-bit/ClackLab.git
cd ClackLab

# Option A: Using uv (recommended)
uv sync --extra dev

# Option B: Standard Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Running in Development

```bash
# Launch interactive application
uv run python main.py

# Launch directly into background accessory mode
uv run python main.py --background

# Launch with preselected profile
uv run python main.py --profile thocky
```

### 3. Headless Latency Benchmarking

To measure scheduling latency and verify hardware buffer integrity without initializing graphical dependencies:

```bash
uv run python main.py --benchmark --profile tactile
```

Benchmark output format:
```
============================================================
CLACKLAB CLI BENCHMARK & AUDIO ENGINE TEST
============================================================
macOS Accessibility Trusted: True
Default Output Device: System Default Audio Output
Discovered 6 switch profiles: ['creamy', 'tactile', 'thocky', 'linear', 'silent', 'clicky']
Testing Switch Profile: Holy Panda (Tactile) (tactile)
Audio engine started: SR=48000Hz, BlockSize=128 (2.67ms latency)

Streaming active. Simulating rapid mechanical typing...
============================================================
BENCHMARK RESULTS:
  Total Keystrokes Measured : 100
  Median Latency (p50)      : 0.308 ms
  95th Percentile (p95)     : 0.690 ms
  Maximum Latency           : 0.880 ms
  Buffer Underruns          : 0
  Configured Buffer Period  : 2.67 ms
============================================================
Audio playback benchmark finished cleanly with zero errors.
```

### 4. Running the Test Suite

The test suite contains 47 unit and integration tests covering audio processing, event filters, state machines, and system integrations:

```bash
uv run pytest
```

---

## Compilation and Packaging

### Compiling macOS Application Bundle (`.app`)

```bash
./scripts/build_app.sh
```

This script:
1. Validates that sound assets and manifests are present.
2. Invokes PyInstaller with required hidden imports (`ServiceManagement`, `Quartz`, `AppKit`, `sounddevice`, `soundfile`).
3. Injects `NSAccessibilityUsageDescription` into `Info.plist`.
4. Codesigns nested dynamic libraries, frameworks, and the root bundle.
5. Produces `dist/ClackLab.app`.

### Generating Compressed Disk Image (`.dmg`)

```bash
./scripts/build_dmg.sh --rebuild
```

This script:
1. Rebuilds `dist/ClackLab.app` if necessary.
2. Stages the bundle alongside an `/Applications` filesystem link.
3. Cleans extended quarantine attributes.
4. Generates an Apple APFS/UDZO compressed disk image at `dist/ClackLab-v1.0.0-macOS.dmg`.

---

## Privacy and Security Specifications

- **Zero Logging Policy**: ClackLab does not store, transmit, or analyze text typed by the user. Keystroke events are discarded immediately after selecting an acoustic sample.
- **Listen-Only Event Tap**: The keyboard monitor operates strictly in `kCGEventTapOptionListenOnly` mode. It is structurally incapable of suppressing, modifying, or delaying keyboard input.
- **No Microphone Access**: Sound generation is pure output; input audio devices are never opened or recorded.
- **Local Execution**: The software functions 100% offline with zero outbound network communication.

---

## License and Attributions

Distributed under the **MIT License**. Refer to [LICENSES.md](LICENSES.md) for full terms, third-party component licenses, and acoustic sample attributions.
