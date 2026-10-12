"""
Script to prepare, normalize, and save standard 48kHz WAV sound assets for ClackLab.
Downloads authentic MIT-licensed mechanical switch recordings from Mechvibes,
processes them (trims leading silence, normalizes gain, applies clean fades),
and packages them into 6 distinct profiles:
  - Linear (Cherry MX Black)
  - Tactile (Holy Panda)
  - Clicky (Cherry MX Blue)
  - Creamy (NK Cream)
  - Thocky (Deep body resonance & PBT bottom-out acoustic filtering)
  - Silent (Silicone-dampened acoustic absorption filtering)
"""

import os
import json
import io
import urllib.request
import soundfile as sf
import numpy as np

TARGET_SR = 48000

def resample_linear(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio
    num_samples = int(len(audio) * target_sr / orig_sr)
    indices = np.linspace(0, len(audio) - 1, num_samples)
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

def trim_and_process(audio: np.ndarray, sr: int, target_peak: float = 0.85) -> np.ndarray:
    # Convert to mono float32 for processing
    if audio.ndim > 1:
        mono = np.mean(audio, axis=1)
    else:
        mono = audio.astype(np.float32)

    # Remove DC offset
    mono = mono - np.mean(mono)

    # Find start threshold (2% of peak)
    peak = np.max(np.abs(mono))
    if peak > 1e-4:
        threshold = peak * 0.02
        non_silent = np.where(np.abs(mono) > threshold)[0]
        if len(non_silent) > 0:
            # Keep a tiny pre-roll (32 samples)
            start_idx = max(0, non_silent[0] - 32)
            mono = mono[start_idx:]

    # Resample to TARGET_SR
    resampled = resample_linear(mono, sr, TARGET_SR)

    # 1ms fade in to avoid click
    fade_in_len = min(len(resampled), int(TARGET_SR * 0.001))
    if fade_in_len > 0:
        resampled[:fade_in_len] *= np.linspace(0, 1, fade_in_len)

    # 5ms fade out at the end
    fade_out_len = min(len(resampled), int(TARGET_SR * 0.005))
    if fade_out_len > 0:
        resampled[-fade_out_len:] *= np.linspace(1, 0, fade_out_len)

    # Normalize peak
    curr_peak = np.max(np.abs(resampled))
    if curr_peak > 1e-4:
        resampled = resampled * (target_peak / curr_peak)

    # Make stereo
    stereo = np.column_stack([resampled, resampled]).astype(np.float32)
    return stereo

def download_audio(url: str) -> tuple[np.ndarray, int]:
    req = urllib.request.Request(url, headers={'User-Agent': 'ClackLab/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    f = io.BytesIO(data)
    audio, sr = sf.read(f)
    return audio, sr

def apply_acoustic_filter(audio_stereo: np.ndarray, profile_type: str) -> np.ndarray:
    """
    Applies custom physical acoustic character for Thocky and Silent profiles:
    - Thocky: rich low-mid cavity resonance (boost 150-350 Hz, roll off highs > 3.5 kHz)
    - Silent: silicone-dampened impact (steep low-pass rolloff > 1.8 kHz, soft envelope)
    """
    data = audio_stereo.copy()
    left = data[:, 0]
    
    # FFT filtering
    fft = np.fft.rfft(left)
    freqs = np.fft.rfftfreq(len(left), d=1.0 / TARGET_SR)

    if profile_type == 'thocky':
        # Boost 120-350 Hz (body resonance), attenuate above 3 kHz
        eq = np.ones_like(freqs)
        low_bump = np.exp(-((freqs - 220) ** 2) / (2 * (90 ** 2))) * 1.8
        eq += low_bump
        high_cut = 1.0 / (1.0 + (np.maximum(0, freqs - 2800) / 1000.0) ** 2)
        eq *= high_cut
        filtered = np.fft.irfft(fft * eq, n=len(left))
    elif profile_type == 'silent':
        # Steep roll-off above 1600 Hz (silicone rail absorption)
        eq = 1.0 / (1.0 + (np.maximum(0, freqs - 1400) / 600.0) ** 4)
        filtered = np.fft.irfft(fft * eq, n=len(left))
        # Soften attack slightly (simulate rubber pad cushion)
        cushion_len = min(len(filtered), int(TARGET_SR * 0.003))
        if cushion_len > 0:
            filtered[:cushion_len] *= np.linspace(0.1, 1.0, cushion_len) ** 2
    else:
        return audio_stereo

    # Re-normalize
    peak = np.max(np.abs(filtered))
    if peak > 1e-4:
        filtered = filtered * (0.85 / peak)

    return np.column_stack([filtered, filtered]).astype(np.float32)

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets", "sounds")
    os.makedirs(assets_dir, exist_ok=True)

    sources = {
        "tactile": {
            "name": "Holy Panda (Tactile)",
            "description": "Distinct tactile bump with full-bodied mechanical clack and snappy return.",
            "base_url": "https://raw.githubusercontent.com/hainguyents13/mechvibes/main/src/audio/holy-pandas",
            "files": {
                "down_1.wav": "GENERIC_R0.mp3",
                "down_2.wav": "GENERIC_R1.mp3",
                "down_3.wav": "GENERIC_R2.mp3",
                "down_4.wav": "GENERIC_R3.mp3",
                "down_5.wav": "GENERIC_R4.mp3",
                "space_down.wav": "SPACE.mp3",
                "enter_down.wav": "ENTER.mp3",
                "backspace_down.wav": "BACKSPACE.mp3",
                "up_1.wav": "release/GENERIC.mp3",
                "space_up.wav": "release/SPACE.mp3",
                "enter_up.wav": "release/ENTER.mp3",
                "backspace_up.wav": "release/BACKSPACE.mp3",
            }
        },
        "clicky": {
            "name": "Cherry MX Blue (Clicky)",
            "description": "Crisp, metallic click leaf snap with distinct tactile release.",
            "base_url": "https://raw.githubusercontent.com/hainguyents13/mechvibes/main/src/audio/mxblue-travel",
            "files": {
                "down_1.wav": "press/GENERIC_R0.mp3",
                "down_2.wav": "press/GENERIC_R1.mp3",
                "down_3.wav": "press/GENERIC_R2.mp3",
                "down_4.wav": "press/GENERIC_R3.mp3",
                "down_5.wav": "press/GENERIC_R4.mp3",
                "space_down.wav": "press/SPACE.mp3",
                "enter_down.wav": "press/ENTER.mp3",
                "backspace_down.wav": "press/BACKSPACE.mp3",
                "up_1.wav": "release/GENERIC.mp3",
                "space_up.wav": "release/SPACE.mp3",
                "enter_up.wav": "release/ENTER.mp3",
                "backspace_up.wav": "release/BACKSPACE.mp3",
            }
        },
        "linear": {
            "name": "Cherry MX Black (Linear)",
            "description": "Smooth slider travel with a solid, clean bottom-out clack.",
            "base_url": "https://raw.githubusercontent.com/hainguyents13/mechvibes/main/src/audio/mxblack-travel",
            "files": {
                "down_1.wav": "press/GENERIC_R0.mp3",
                "down_2.wav": "press/GENERIC_R1.mp3",
                "down_3.wav": "press/GENERIC_R2.mp3",
                "down_4.wav": "press/GENERIC_R3.mp3",
                "down_5.wav": "press/GENERIC_R4.mp3",
                "space_down.wav": "press/SPACE.mp3",
                "enter_down.wav": "press/ENTER.mp3",
                "backspace_down.wav": "press/BACKSPACE.mp3",
                "up_1.wav": "release/GENERIC.mp3",
                "space_up.wav": "release/SPACE.mp3",
                "enter_up.wav": "release/ENTER.mp3",
                "backspace_up.wav": "release/BACKSPACE.mp3",
            }
        },
        "creamy": {
            "name": "NovelKeys Cream (Creamy)",
            "description": "Smooth, rounded, marbly mechanical typing feel with soft acoustics.",
            "base_url": "https://raw.githubusercontent.com/hainguyents13/mechvibes/main/src/audio/cream-travel",
            "files": {
                "down_1.wav": "press/GENERIC_R0.mp3",
                "down_2.wav": "press/GENERIC_R1.mp3",
                "down_3.wav": "press/GENERIC_R2.mp3",
                "down_4.wav": "press/GENERIC_R3.mp3",
                "down_5.wav": "press/GENERIC_R4.mp3",
                "space_down.wav": "press/SPACE.mp3",
                "enter_down.wav": "press/ENTER.mp3",
                "backspace_down.wav": "press/BACKSPACE.mp3",
                "up_1.wav": "release/GENERIC.mp3",
                "space_up.wav": "release/SPACE.mp3",
                "enter_up.wav": "release/ENTER.mp3",
                "backspace_up.wav": "release/BACKSPACE.mp3",
            }
        }
    }

    manifest_all = {}

    for profile_id, info in sources.items():
        print(f"Downloading and processing profile: {profile_id} ({info['name']})...")
        prof_dir = os.path.join(assets_dir, profile_id)
        os.makedirs(prof_dir, exist_ok=True)
        
        down_samples = []
        up_samples = []
        space_down = None
        space_up = None
        enter_down = None
        enter_up = None
        backspace_down = None
        backspace_up = None

        for out_name, rel_url in info["files"].items():
            url = f"{info['base_url']}/{rel_url}"
            try:
                raw, sr = download_audio(url)
                processed = trim_and_process(raw, sr)
                out_path = os.path.join(prof_dir, out_name)
                sf.write(out_path, processed, TARGET_SR, subtype='PCM_16')
                
                if out_name.startswith("down_"):
                    down_samples.append(out_name)
                elif out_name.startswith("up_"):
                    up_samples.append(out_name)
                elif out_name == "space_down.wav":
                    space_down = out_name
                elif out_name == "space_up.wav":
                    space_up = out_name
                elif out_name == "enter_down.wav":
                    enter_down = out_name
                elif out_name == "enter_up.wav":
                    enter_up = out_name
                elif out_name == "backspace_down.wav":
                    backspace_down = out_name
                elif out_name == "backspace_up.wav":
                    backspace_up = out_name
            except Exception as e:
                print(f"  Warning: failed to fetch {url}: {e}")

        manifest = {
            "id": profile_id,
            "name": info["name"],
            "description": info["description"],
            "version": "1.0.0",
            "author": "Mechvibes Community / ClackLab",
            "license": "MIT",
            "sample_rate": TARGET_SR,
            "channels": 2,
            "down_samples": down_samples,
            "up_samples": up_samples,
            "special_keys": {
                "space": {"down": space_down, "up": space_up},
                "enter": {"down": enter_down, "up": enter_up},
                "backspace": {"down": backspace_down, "up": backspace_up}
            },
            "gain": 1.0,
            "press_gain": 1.0,
            "release_gain": 0.75
        }
        with open(os.path.join(prof_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        manifest_all[profile_id] = manifest

    # Generate Thocky from Holy Panda with low-end cavity resonance & PBT deep thock acoustic profile
    print("Generating Thocky profile (Boba U4T / PBT Deep Resonance)...")
    thocky_dir = os.path.join(assets_dir, "thocky")
    os.makedirs(thocky_dir, exist_ok=True)
    tactile_dir = os.path.join(assets_dir, "tactile")
    thocky_manifest = json.loads(json.dumps(manifest_all["tactile"]))
    thocky_manifest["id"] = "thocky"
    thocky_manifest["name"] = "Boba U4T (Thocky)"
    thocky_manifest["description"] = "Deep, resonant, low-pitched bottom-out sound characteristic of lubed PBT keycaps."

    for out_name in os.listdir(tactile_dir):
        if out_name.endswith(".wav"):
            audio, sr = sf.read(os.path.join(tactile_dir, out_name))
            thock_audio = apply_acoustic_filter(audio, 'thocky')
            sf.write(os.path.join(thocky_dir, out_name), thock_audio, TARGET_SR, subtype='PCM_16')

    with open(os.path.join(thocky_dir, "manifest.json"), "w") as f:
        json.dump(thocky_manifest, f, indent=2)
    manifest_all["thocky"] = thocky_manifest

    # Generate Silent from Linear with silicone pad damping acoustic profile
    print("Generating Silent profile (Silent Cherry / Silicone Damped)...")
    silent_dir = os.path.join(assets_dir, "silent")
    os.makedirs(silent_dir, exist_ok=True)
    linear_dir = os.path.join(assets_dir, "linear")
    silent_manifest = json.loads(json.dumps(manifest_all["linear"]))
    silent_manifest["id"] = "silent"
    silent_manifest["name"] = "Cherry MX Silent (Dampened)"
    silent_manifest["description"] = "Muted, quiet mechanical sound with silicone-cushioned rail impact and suppressed high frequencies."

    for out_name in os.listdir(linear_dir):
        if out_name.endswith(".wav"):
            audio, sr = sf.read(os.path.join(linear_dir, out_name))
            silent_audio = apply_acoustic_filter(audio, 'silent')
            sf.write(os.path.join(silent_dir, out_name), silent_audio, TARGET_SR, subtype='PCM_16')

    with open(os.path.join(silent_dir, "manifest.json"), "w") as f:
        json.dump(silent_manifest, f, indent=2)
    manifest_all["silent"] = silent_manifest

    # Master manifest
    with open(os.path.join(assets_dir, "manifest.json"), "w") as f:
        json.dump(manifest_all, f, indent=2)

    print("All 6 switch profiles successfully generated and packaged!")

if __name__ == "__main__":
    main()
