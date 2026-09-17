"""
Drum pattern library and algorithmic generator.

All times and durations are in beats (quarter notes).
4.0 beats = 1 bar.

GM drum pitches used throughout:
  36 = Bass Drum 1       42 = Closed Hi-Hat   49 = Crash Cymbal
  38 = Acoustic Snare    46 = Open Hi-Hat      51 = Ride Cymbal
  37 = Side Stick        44 = Pedal Hi-Hat     55 = Splash
  40 = Electric Snare    47 = Low-Mid Tom      43 = High Floor Tom
  41 = Low Floor Tom     48 = Hi-Mid Tom       50 = High Tom
"""

from __future__ import annotations
import random
from typing import TypedDict


class Note(TypedDict):
    pitch: int
    time: float
    duration: float
    velocity: int


# ---------------------------------------------------------------------------
# Pre-built patterns (1 bar = 4 beats each)
# ---------------------------------------------------------------------------

def _hat(div: float, bars: int = 1, vel: int = 80) -> list[Note]:
    """Closed hi-hat on a regular grid."""
    notes = []
    t = 0.0
    total = bars * 4.0
    while t < total - 1e-9:
        notes.append(Note(pitch=42, time=round(t, 4), duration=div / 2, velocity=vel))
        t += div
    return notes


PRESET_PATTERNS: dict[str, list[Note]] = {
    # ------------------------------------------------------------------ #
    "rock_basic": [
        # kick on 1 and 3
        Note(pitch=36, time=0.0, duration=0.25, velocity=110),
        Note(pitch=36, time=2.0, duration=0.25, velocity=105),
        # snare on 2 and 4
        Note(pitch=38, time=1.0, duration=0.25, velocity=115),
        Note(pitch=38, time=3.0, duration=0.25, velocity=115),
        # 8th-note hi-hats
        *_hat(0.5),
    ],
    # ------------------------------------------------------------------ #
    "rock_driving": [
        Note(pitch=36, time=0.0,  duration=0.25, velocity=110),
        Note(pitch=36, time=0.5,  duration=0.25, velocity=75),
        Note(pitch=36, time=2.0,  duration=0.25, velocity=110),
        Note(pitch=36, time=2.75, duration=0.25, velocity=70),
        Note(pitch=38, time=1.0,  duration=0.25, velocity=115),
        Note(pitch=38, time=3.0,  duration=0.25, velocity=115),
        Note(pitch=49, time=0.0,  duration=0.25, velocity=90),  # crash on 1
        *_hat(0.25),  # 16th-note hats
    ],
    # ------------------------------------------------------------------ #
    "funk": [
        Note(pitch=36, time=0.0,  duration=0.25, velocity=110),
        Note(pitch=36, time=0.75, duration=0.25, velocity=80),
        Note(pitch=36, time=2.0,  duration=0.25, velocity=105),
        Note(pitch=36, time=2.5,  duration=0.25, velocity=70),
        Note(pitch=38, time=1.0,  duration=0.25, velocity=115),
        Note(pitch=38, time=1.75, duration=0.25, velocity=50),  # ghost
        Note(pitch=38, time=3.0,  duration=0.25, velocity=115),
        Note(pitch=38, time=3.5,  duration=0.25, velocity=50),  # ghost
        Note(pitch=46, time=0.75, duration=0.125, velocity=90),
        Note(pitch=46, time=2.75, duration=0.125, velocity=90),
        *_hat(0.25, vel=72),
    ],
    # ------------------------------------------------------------------ #
    "jazz_swing": [
        # Ride swing (triplet subdivisions approximated)
        Note(pitch=51, time=0.0,   duration=0.125, velocity=85),
        Note(pitch=51, time=0.333, duration=0.125, velocity=65),
        Note(pitch=51, time=0.667, duration=0.125, velocity=80),
        Note(pitch=51, time=1.0,   duration=0.125, velocity=85),
        Note(pitch=51, time=1.333, duration=0.125, velocity=65),
        Note(pitch=51, time=1.667, duration=0.125, velocity=80),
        Note(pitch=51, time=2.0,   duration=0.125, velocity=85),
        Note(pitch=51, time=2.333, duration=0.125, velocity=65),
        Note(pitch=51, time=2.667, duration=0.125, velocity=80),
        Note(pitch=51, time=3.0,   duration=0.125, velocity=85),
        Note(pitch=51, time=3.333, duration=0.125, velocity=65),
        Note(pitch=51, time=3.667, duration=0.125, velocity=80),
        # Brush snare
        Note(pitch=38, time=1.0,  duration=0.25, velocity=55),
        Note(pitch=38, time=3.0,  duration=0.25, velocity=55),
        # Sparse kick
        Note(pitch=36, time=0.0,  duration=0.25, velocity=75),
        Note(pitch=36, time=2.5,  duration=0.25, velocity=65),
        # Hi-hat foot on 2 and 4
        Note(pitch=44, time=1.0,  duration=0.125, velocity=90),
        Note(pitch=44, time=3.0,  duration=0.125, velocity=90),
    ],
    # ------------------------------------------------------------------ #
    "trap": [
        Note(pitch=36, time=0.0,  duration=0.5,  velocity=120),
        Note(pitch=36, time=1.5,  duration=0.25, velocity=100),
        Note(pitch=36, time=2.75, duration=0.25, velocity=110),
        Note(pitch=38, time=1.0,  duration=0.25, velocity=115),
        Note(pitch=38, time=3.0,  duration=0.25, velocity=115),
        Note(pitch=46, time=0.5,  duration=0.125, velocity=95),
        Note(pitch=46, time=2.5,  duration=0.125, velocity=95),
        # 32nd-note hi-hat roll
        *[Note(pitch=42, time=round(i * 0.125, 4), duration=0.0625,
               velocity=55 + (i % 4) * 8) for i in range(32)],
    ],
    # ------------------------------------------------------------------ #
    "reggae_one_drop": [
        Note(pitch=36, time=2.0,  duration=0.25, velocity=110),
        Note(pitch=38, time=2.0,  duration=0.25, velocity=100),
        Note(pitch=37, time=0.0,  duration=0.125, velocity=85),
        Note(pitch=37, time=2.0,  duration=0.125, velocity=85),
        Note(pitch=42, time=0.5,  duration=0.125, velocity=80),
        Note(pitch=42, time=1.5,  duration=0.125, velocity=80),
        Note(pitch=42, time=2.5,  duration=0.125, velocity=80),
        Note(pitch=42, time=3.5,  duration=0.125, velocity=80),
    ],
    # ------------------------------------------------------------------ #
    "bossa_nova": [
        Note(pitch=37, time=0.0,  duration=0.125, velocity=90),
        Note(pitch=37, time=0.5,  duration=0.125, velocity=85),
        Note(pitch=37, time=1.0,  duration=0.125, velocity=78),
        Note(pitch=37, time=1.5,  duration=0.125, velocity=85),
        Note(pitch=37, time=2.0,  duration=0.125, velocity=78),
        Note(pitch=37, time=2.5,  duration=0.125, velocity=90),
        Note(pitch=37, time=3.0,  duration=0.125, velocity=85),
        Note(pitch=37, time=3.5,  duration=0.125, velocity=85),
        Note(pitch=36, time=0.0,  duration=0.25, velocity=85),
        Note(pitch=36, time=1.0,  duration=0.25, velocity=78),
        Note(pitch=36, time=2.0,  duration=0.25, velocity=82),
        Note(pitch=36, time=3.0,  duration=0.25, velocity=78),
        Note(pitch=42, time=1.0,  duration=0.125, velocity=68),
        Note(pitch=42, time=3.0,  duration=0.125, velocity=68),
    ],
    # ------------------------------------------------------------------ #
    "half_time": [
        Note(pitch=36, time=0.0,  duration=0.25, velocity=110),
        Note(pitch=36, time=0.5,  duration=0.25, velocity=68),
        Note(pitch=38, time=2.0,  duration=0.25, velocity=115),
        Note(pitch=46, time=1.5,  duration=0.25, velocity=90),
        *_hat(0.5, vel=72),
    ],
    # ------------------------------------------------------------------ #
    "drum_fill_4bar": [
        # Standard 3-bar groove + 1-bar fill
        Note(pitch=36, time=0.0,  duration=0.25, velocity=110),
        Note(pitch=36, time=2.0,  duration=0.25, velocity=105),
        Note(pitch=38, time=1.0,  duration=0.25, velocity=115),
        Note(pitch=38, time=3.0,  duration=0.25, velocity=115),
        *_hat(0.5),
        # Fill in bar 4
        Note(pitch=50, time=12.5, duration=0.25, velocity=100),
        Note(pitch=48, time=12.75,duration=0.25, velocity=100),
        Note(pitch=47, time=13.0, duration=0.25, velocity=100),
        Note(pitch=45, time=13.25,duration=0.25, velocity=100),
        Note(pitch=43, time=13.5, duration=0.25, velocity=100),
        Note(pitch=41, time=13.75,duration=0.25, velocity=100),
        Note(pitch=36, time=14.0, duration=0.25, velocity=120),
        Note(pitch=49, time=14.0, duration=0.25, velocity=110),
    ],
}


def list_patterns() -> list[str]:
    return list(PRESET_PATTERNS.keys())


def get_pattern(name: str) -> list[Note]:
    if name not in PRESET_PATTERNS:
        raise ValueError(f"Unknown pattern {name!r}. Available: {list_patterns()}")
    return PRESET_PATTERNS[name]


# ---------------------------------------------------------------------------
# Algorithmic generator
# ---------------------------------------------------------------------------

def generate_pattern(
    style: str = "rock",
    complexity: float = 0.5,
    bars: int = 1,
    swing: bool = False,
    seed: int | None = None,
) -> list[Note]:
    """
    Generate a drum pattern algorithmically.

    Parameters
    ----------
    style:      "rock" | "funk" | "jazz" | "trap" | "reggae" | "half_time"
    complexity: 0.0 (sparse/simple) … 1.0 (dense/complex)
    bars:       number of bars (4 beats each)
    swing:      nudge off-beat 8th notes back by 1/3 of a beat
    seed:       optional RNG seed for reproducibility
    """
    rng = random.Random(seed)
    beats = bars * 4.0
    notes: list[Note] = []

    if style in ("rock", "pop"):
        # ----- kick -----
        kick_times = [0.0, 2.0]
        if complexity > 0.35:
            kick_times.append(2.5)
        if complexity > 0.65:
            kick_times += [0.5, 3.5]
        for b in range(bars):
            off = b * 4.0
            for t in kick_times:
                vel = int(rng.uniform(100, 115))
                notes.append(Note(pitch=36, time=off + t, duration=0.25, velocity=vel))

        # ----- snare -----
        for b in range(bars):
            off = b * 4.0
            for t in [1.0, 3.0]:
                notes.append(Note(pitch=38, time=off + t, duration=0.25,
                                  velocity=int(rng.uniform(108, 118))))
            if complexity > 0.5:
                notes.append(Note(pitch=38, time=off + 3.5, duration=0.125,
                                  velocity=int(rng.uniform(45, 60))))

        # ----- hi-hat -----
        div = 0.25 if complexity > 0.4 else 0.5
        for b in range(bars):
            off = b * 4.0
            t = 0.0
            while t < 4.0 - 1e-9:
                vel = int(rng.uniform(70, 88)) if t % 0.5 < 1e-9 else int(rng.uniform(58, 75))
                notes.append(Note(pitch=42, time=off + t, duration=div / 2, velocity=vel))
                t += div

        # crash on bar 1 beat 1
        if complexity > 0.3:
            notes.append(Note(pitch=49, time=0.0, duration=0.25, velocity=90))

    elif style == "funk":
        for b in range(bars):
            off = b * 4.0
            kick_syncs = [0.0, 0.75, 2.0, 2.5]
            if complexity > 0.6:
                kick_syncs.append(rng.choice([0.25, 1.25, 3.25]))
            for t in kick_syncs:
                notes.append(Note(pitch=36, time=off + t, duration=0.25,
                                  velocity=int(rng.uniform(95, 115))))
            # snare
            for t in [1.0, 3.0]:
                notes.append(Note(pitch=38, time=off + t, duration=0.25,
                                  velocity=int(rng.uniform(108, 118))))
            # ghost notes
            ghost_vel = int(40 + complexity * 35)
            for t in [0.5, 1.5, 2.5, 3.5]:
                if rng.random() < complexity:
                    notes.append(Note(pitch=38, time=off + t, duration=0.125,
                                      velocity=ghost_vel))
            # 16th hats
            t = 0.0
            while t < 4.0 - 1e-9:
                vel = int(rng.uniform(72, 85)) if t % 0.5 < 1e-9 else int(rng.uniform(55, 70))
                notes.append(Note(pitch=42, time=off + t, duration=0.125, velocity=vel))
                t += 0.25
            # open hat accents
            for t in [0.75, 2.75]:
                if rng.random() < 0.6 + complexity * 0.4:
                    notes.append(Note(pitch=46, time=off + t, duration=0.125,
                                      velocity=int(rng.uniform(85, 95))))

    elif style == "jazz":
        # Ride-centric swing
        for b in range(bars):
            off = b * 4.0
            for beat in range(4):
                base = off + beat
                notes.append(Note(pitch=51, time=base + 0.0,   duration=0.125, velocity=int(rng.uniform(78, 90))))
                notes.append(Note(pitch=51, time=base + 0.333, duration=0.125, velocity=int(rng.uniform(60, 72))))
                notes.append(Note(pitch=51, time=base + 0.667, duration=0.125, velocity=int(rng.uniform(75, 88))))
            # brush snare
            for t in [1.0, 3.0]:
                notes.append(Note(pitch=38, time=off + t, duration=0.25,
                                  velocity=int(rng.uniform(50, 65))))
            # walking kick
            kick_beats = [0.0]
            if complexity > 0.3:
                kick_beats.append(2.5)
            if complexity > 0.6:
                kick_beats.append(rng.choice([1.5, 3.5]))
            for t in kick_beats:
                notes.append(Note(pitch=36, time=off + t, duration=0.25,
                                  velocity=int(rng.uniform(65, 80))))
            # hi-hat foot
            for t in [1.0, 3.0]:
                notes.append(Note(pitch=44, time=off + t, duration=0.125, velocity=88))

    elif style == "trap":
        for b in range(bars):
            off = b * 4.0
            # 808 kick
            notes.append(Note(pitch=36, time=off + 0.0, duration=0.5, velocity=120))
            if complexity > 0.3:
                notes.append(Note(pitch=36, time=off + 1.5, duration=0.25, velocity=100))
            if complexity > 0.6:
                notes.append(Note(pitch=36, time=off + 2.75, duration=0.25,
                                  velocity=int(rng.uniform(95, 110))))
            # snare
            for t in [1.0, 3.0]:
                notes.append(Note(pitch=38, time=off + t, duration=0.25, velocity=115))
            # hi-hat roll density scales with complexity
            div = 0.125 if complexity > 0.5 else 0.25
            t = 0.0
            while t < 4.0 - 1e-9:
                vel = int(rng.uniform(50, 75))
                notes.append(Note(pitch=42, time=off + t, duration=div / 2, velocity=vel))
                t += div
            # open hat accent
            for t in [0.5, 2.5]:
                if rng.random() < complexity:
                    notes.append(Note(pitch=46, time=off + t, duration=0.125,
                                      velocity=int(rng.uniform(88, 98))))

    elif style == "reggae":
        for b in range(bars):
            off = b * 4.0
            notes.append(Note(pitch=36, time=off + 2.0, duration=0.25, velocity=110))
            notes.append(Note(pitch=38, time=off + 2.0, duration=0.25, velocity=100))
            for t in [0.0, 2.0]:
                notes.append(Note(pitch=37, time=off + t, duration=0.125, velocity=85))
            for t in [0.5, 1.5, 2.5, 3.5]:
                notes.append(Note(pitch=42, time=off + t, duration=0.125, velocity=78))

    elif style == "half_time":
        for b in range(bars):
            off = b * 4.0
            notes.append(Note(pitch=36, time=off + 0.0, duration=0.25, velocity=110))
            notes.append(Note(pitch=36, time=off + 0.5, duration=0.25, velocity=68))
            notes.append(Note(pitch=38, time=off + 2.0, duration=0.25, velocity=115))
            if complexity > 0.4:
                notes.append(Note(pitch=46, time=off + 1.5, duration=0.25, velocity=88))
            t = 0.0
            while t < 4.0 - 1e-9:
                notes.append(Note(pitch=42, time=off + t, duration=0.25, velocity=72))
                t += 0.5
    else:
        return generate_pattern("rock", complexity, bars, swing, seed)

    # Apply swing (push off-beat 8th notes by ~1/3 beat)
    if swing:
        swung = []
        for n in notes:
            t = n["time"]
            bar_local = t % 4.0
            bar_offset = t - bar_local
            eighth_idx = bar_local / 0.5
            if abs(eighth_idx % 2 - 1) < 0.05:  # on an off-beat 8th
                t = bar_offset + round(eighth_idx) * 0.5 - 0.5 + 0.333
            swung.append({**n, "time": round(t, 4)})
        notes = swung

    # Deduplicate notes at the same pitch+time (keep highest velocity)
    seen: dict[tuple, Note] = {}
    for n in notes:
        key = (n["pitch"], round(n["time"], 3))
        if key not in seen or n["velocity"] > seen[key]["velocity"]:
            seen[key] = n

    return sorted(seen.values(), key=lambda n: (n["time"], n["pitch"]))


# ---------------------------------------------------------------------------
# Chord-to-style helper (used by auto-drummer when keyboard input detected)
# ---------------------------------------------------------------------------

SCALE_TO_STYLE: dict[str, str] = {
    "major":      "rock",
    "minor":      "rock",
    "dorian":     "funk",
    "mixolydian": "funk",
    "pentatonic": "blues",
    "blues":      "funk",
    "chromatic":  "jazz",
}


def guess_style_from_notes(midi_notes: list[int]) -> str:
    """Very rough style guess based on interval content of held notes."""
    if len(midi_notes) < 2:
        return "rock"
    intervals = sorted({(b - a) % 12 for a, b in zip(midi_notes, midi_notes[1:])})
    # Minor 7th / 9th chord fragments → funk/jazz
    if any(i in intervals for i in [10, 11, 2]):
        return "funk"
    # Tritone → jazz
    if 6 in intervals:
        return "jazz"
    # Minor third only → rock/minor
    return "rock"
