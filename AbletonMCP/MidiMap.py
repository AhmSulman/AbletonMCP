# AKAI MPD218 - Factory Preset 1 (GM Drums)
# Pads send on MIDI channel 10 (0-indexed: 9)
MPD218_CHANNEL = 9  # 0-indexed

# Pad number (1=bottom-left, 16=top-right) -> MIDI note
MPD218_PAD_NOTES = {
    1:  36,  # Bass Drum 1
    2:  38,  # Acoustic Snare
    3:  42,  # Closed Hi-Hat
    4:  46,  # Open Hi-Hat
    5:  48,  # Hi-Mid Tom
    6:  47,  # Low-Mid Tom
    7:  45,  # Low Tom
    8:  43,  # High Floor Tom
    9:  49,  # Crash Cymbal 1
    10: 51,  # Ride Cymbal 1
    11: 50,  # High Tom
    12: 55,  # Splash Cymbal
    13: 40,  # Electric Snare
    14: 37,  # Side Stick
    15: 41,  # Low Floor Tom
    16: 35,  # Acoustic Bass Drum
}

# MPD218 knobs send CC on channel 1 (0-indexed: 0)
MPD218_KNOB_CHANNEL = 0
MPD218_KNOB_CCS = {
    1: 3,
    2: 9,
    3: 12,
    4: 13,
    5: 14,
    6: 15,
}

# M-Audio Oxygen 49 (5th gen) transport CCs, channel 1 (0-indexed: 0)
OXYGEN49_CHANNEL = 0
OXYGEN49_TRANSPORT_CCS = {
    "rewind":   19,
    "ff":       20,
    "stop":     21,
    "play":     22,
    "record":   23,
    "loop":     24,
}

# Oxygen 49 knobs K1-K8, channel 1
OXYGEN49_KNOB_CCS = {
    1: 75,
    2: 76,
    3: 77,
    4: 78,
    5: 79,
    6: 80,
    7: 81,
    8: 82,
}

# ─────────────────────────────────────────────────────────────────────────────
# AKAI APC40 Mk2 — 64 pads + 9 faders + knobs + transport (default mapping)
# ─────────────────────────────────────────────────────────────────────────────

APC40_CHANNEL = 0  # MIDI channel 1 (0-indexed)

# 8×8 pad grid: rows 0–7, columns 0–7. Factory default notes: 36–99.
# Row 0 (bottom) = pads 0–7, Row 7 (top) = pads 56–63
APC40_GRID_WIDTH = 8
APC40_GRID_HEIGHT = 8
APC40_PAD_NOTE_BASE = 36  # Note 36 (C2) is bottom-left pad [0,0]

# 9 vertical faders (CC 48–56)
APC40_FADER_CCS = {
    0: 48,  # Master fader
    1: 49,  # Track 1
    2: 50,  # Track 2
    3: 51,  # Track 3
    4: 52,  # Track 4
    5: 53,  # Track 5
    6: 54,  # Track 6
    7: 55,  # Track 7
    8: 56,  # Track 8
}

# 8 rotary knobs below grid (CC 16–23)
APC40_KNOB_CCS = {
    1: 16,  # Knob 1
    2: 17,  # Knob 2
    3: 18,  # Knob 3
    4: 19,  # Knob 4
    5: 20,  # Knob 5
    6: 21,  # Knob 6
    7: 22,  # Knob 7
    8: 23,  # Knob 8
}

# Transport controls (buttons send notes on channel 2, 0-indexed: 1)
APC40_TRANSPORT_CHANNEL = 1
APC40_TRANSPORT_NOTES = {
    "clip_stop":  51,
    "clip_launch": 52,
    "scene_stop": 53,
    "scene_launch": 54,
}

# Buttons (additional CC/note mappings as needed)
APC40_BUTTON_CCS = {
    "shift":      98,  # Shift button
    "bank_left":  52,  # Bank left
    "bank_right": 53,  # Bank right
}

# General MIDI drum note reference (pitch -> name)
GM_DRUMS = {
    35: "Acoustic Bass Drum",
    36: "Bass Drum 1",
    37: "Side Stick",
    38: "Acoustic Snare",
    39: "Hand Clap",
    40: "Electric Snare",
    41: "Low Floor Tom",
    42: "Closed Hi-Hat",
    43: "High Floor Tom",
    44: "Pedal Hi-Hat",
    45: "Low Tom",
    46: "Open Hi-Hat",
    47: "Low-Mid Tom",
    48: "Hi-Mid Tom",
    49: "Crash Cymbal 1",
    50: "High Tom",
    51: "Ride Cymbal 1",
    53: "Ride Bell",
    55: "Splash Cymbal",
    56: "Cowbell",
    57: "Crash Cymbal 2",
    59: "Ride Cymbal 2",
}
