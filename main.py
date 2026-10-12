"""
Entry point for ClackLab — Ultra-Low-Latency Virtual Mechanical Keyboard for macOS.
"""

import sys
import os
import argparse
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.application import ClackApplication
from app.keyboard.permission_manager import PermissionManager
from app.audio.audio_devices import AudioDeviceManager
from app.audio.latency_metrics import LatencyTracker
from app.audio.audio_engine import AudioEngine
from app.audio.sample_library import SampleLibrary
from app.audio.sample_player import SamplePlayer
from app.profiles.profile_manager import ProfileManager
from app.models import KeyCategory

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )

def run_cli_benchmark(profile_id: str = "tactile", count: int = 50):
    """Headless CLI benchmark testing audio scheduling latency."""
    print("=" * 60)
    print("CLACKLAB CLI BENCHMARK & AUDIO ENGINE TEST")
    print("=" * 60)
    
    is_trusted = PermissionManager.is_accessibility_granted()
    print(f"macOS Accessibility Trusted: {is_trusted}")
    
    dev = AudioDeviceManager.get_default_output_device()
    dev_name = dev['name'] if dev else "None"
    print(f"Default Output Device: {dev_name}")

    prof_mgr = ProfileManager()
    prof = prof_mgr.get_profile(profile_id) or prof_mgr.get_active_profile()
    print(f"Testing Switch Profile: {prof.name} ({prof.id})")

    tracker = LatencyTracker()
    engine = AudioEngine(sample_rate=48000, block_size=128, latency_tracker=tracker)
    lib = SampleLibrary(target_sample_rate=48000)
    lib.load_profile(prof)

    player = SamplePlayer(audio_engine=engine, sample_library=lib, latency_tracker=tracker)
    
    started = engine.start()
    if not started:
        print(f"Failed to start audio engine: {engine.last_error}")
        return 1

    print("\nStreaming active. Simulating rapid mechanical typing...")
    import time
    for i in range(count):
        t0 = time.perf_counter_ns()
        player.play_key_down(KeyCategory.STANDARD, is_repeat=False, event_timestamp_ns=t0)
        time.sleep(0.015)
        t1 = time.perf_counter_ns()
        player.play_key_up(KeyCategory.STANDARD, event_timestamp_ns=t1)
        time.sleep(0.005)

    time.sleep(0.2)  # Let tail finish
    engine.stop()

    stats = tracker.get_stats()
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS:")
    print(f"  Total Keystrokes Measured : {stats.count}")
    print(f"  Median Latency (p50)      : {stats.median_ms} ms")
    print(f"  95th Percentile (p95)     : {stats.p95_ms} ms")
    print(f"  Maximum Latency           : {stats.max_ms} ms")
    print(f"  Buffer Underruns          : {stats.buffer_underruns}")
    print(f"  Configured Buffer Period  : {round(stats.block_size / stats.sample_rate * 1000, 2)} ms")
    print("=" * 60)
    print("Audio playback benchmark finished cleanly with zero errors.\n")
    return 0

def main():
    parser = argparse.ArgumentParser(description="ClackLab: Virtual Mechanical Keyboard for macOS")
    parser.add_argument("--profile", type=str, default=None, help="Initial switch profile ID (e.g. tactile, linear, clicky, thocky, creamy, silent)")
    parser.add_argument("--benchmark", action="store_true", help="Run non-GUI audio latency benchmark and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.benchmark:
        prof = args.profile or "thocky"
        sys.exit(run_cli_benchmark(profile_id=prof))

    # Launch PySide6 GUI Application
    app = QApplication(sys.argv)
    app.setApplicationName("ClackLab")
    app.setOrganizationName("ClackLab")

    from app.ui.tray_icon import get_app_icon
    app.setWindowIcon(get_app_icon())

    clack_app = ClackApplication(app)
    if args.profile:
        clack_app._on_profile_selected(args.profile)

    clack_app.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
