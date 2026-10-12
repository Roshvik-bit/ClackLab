# ClackLab Sound Assets Directory

This directory contains pre-processed, high-fidelity mechanical keyboard sound profiles formatted for ultra-low latency playback.

## Directory Structure

```
assets/sounds/
├── manifest.json        # Master sound pack registry
├── linear/             # Cherry MX Black profile (smooth slider, solid bottom-out)
├── tactile/            # Holy Panda profile (prominent tactile bump & crisp clack)
├── clicky/             # Cherry MX Blue profile (crisp click leaf snap)
├── silent/             # Silent Cherry profile (silicone-padded acoustic damping)
├── thocky/             # Boba U4T profile (deep resonant cavity & PBT bottom-out)
└── creamy/             # NovelKeys Cream profile (silky smooth marbly acoustics)
```

## Sound File Format Specifications
Each switch profile directory contains:
- `manifest.json`: Metadata, profile description, gain offsets, and sample mapping.
- `down_1.wav` ... `down_5.wav`: 5 distinct key-down recordings for natural round-robin variation without repetition.
- `up_1.wav`: Key-up release sound.
- `space_down.wav`, `space_up.wav`: Dedicated spacebar stabilizer sounds.
- `enter_down.wav`, `enter_up.wav`: Dedicated enter key stabilizer sounds.
- `backspace_down.wav`, `backspace_up.wav`: Dedicated backspace stabilizer sounds.

All built-in WAV files are formatted at **48,000 Hz, 16-bit PCM Stereo**. Leading silence has been trimmed to < 1ms to eliminate audible triggering lag.

## Importing Custom Sound Packs
ClackLab supports importing custom sound packs:
1. Native ClackLab Sound Pack format (`manifest.json` with WAV files).
2. Mechvibes Sound Pack format (`config.json` with individual WAV/MP3 files or single sound sprites).

To import, use the **Sound Packs** tab in ClackLab or place the folder in `~/Library/Application Support/ClackLab/soundpacks/`.
