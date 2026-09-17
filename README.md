# AbletonMCP

Control a live Ableton Live session from Claude (or any [MCP](https://modelcontextprotocol.io)-compatible client) — read session state, create tracks and clips, write MIDI, generate drum patterns, and drive hardware controllers (Akai APC40 Mk2, Akai MPD218, M-Audio Oxygen 49), all through natural-language tool calls.

> "Generate a funk drum pattern on track 0, slot 1 at complexity 0.7 and launch it."
> "Set tempo to 95 BPM."
> "Read the pads I'm holding on the APC40 and turn them into a clip."

## How it works

Three pieces talk to each other over two hops:

```
┌────────────────────────┐   MCP protocol    ┌──────────────────┐   TCP / JSON    ┌───────────────────────┐
│  Claude Desktop /       │ ───(stdio)──────► │  mcp_server.py    │ ──(:9877)─────► │  AbletonMCP Remote     │
│  Claude Code            │ ◄─────────────────│  (MCP server)     │ ◄────────────── │  Script (in Live)      │
└────────────────────────┘                    └──────────────────┘                  └───────────┬───────────┘
                                                                                                   │
                                                                                                   ▼
                                                                                          ┌──────────────────┐
                                                                                          │  Ableton Live     │
                                                                                          │  session, tracks, │
                                                                                          │  clips, devices    │
                                                                                          └──────────────────┘
                                                                                                   ▲
                                                                                          MIDI in (optional)
                                                                                          APC40 / MPD218 / Oxygen 49
```

1. **Ableton Remote Script** (`AbletonMCP/`) — a Control Surface script installed into Ableton's Remote Scripts folder. It runs inside Live's embedded Python interpreter, opens a TCP JSON server on `localhost:9877`, and reads raw MIDI from connected controllers.
2. **MCP server** (`mcp_server.py`) — a standalone Python process your MCP client (Claude Desktop or Claude Code) spawns over stdio. It exposes ~24 tools (`ableton_*`) and translates each call into a JSON command sent to port 9877.
3. **Claude** — calls tools like `ableton_set_tempo` or `ableton_generate_drum_pattern`; the two pieces above carry the command through to Live and return real session data.

## Features

- **Session & transport** — read a full session snapshot (tempo, play state, tracks, clips, devices, scenes), play/stop, set tempo.
- **Track control** — create MIDI tracks, rename, set volume/pan, mute/solo.
- **Clip control** — create clips, write raw MIDI notes, rename, fire/stop.
- **Device control** — set any device parameter by index.
- **AI drummer** — algorithmically generate drum patterns (`rock`, `pop`, `funk`, `jazz`, `trap`, `reggae`, `half_time`) with adjustable complexity, bar length, swing, and a seed for reproducibility, or drop in one of 8 hand-crafted presets (`rock_basic`, `rock_driving`, `funk`, `jazz_swing`, `trap`, `reggae_one_drop`, `bossa_nova`, `half_time`, `drum_fill_4bar`).
- **Live auto-drummer** — reads whatever chord/notes are currently held on an Oxygen 49 keyboard and generates a matching pattern in real time.
- **APC40 Mk2 grid control** — read currently-pressed pads, map the 8×8 grid straight to a drum kit, or convert a held pad chord into a playable step sequence.

## Requirements

- Ableton Live with Remote Script support (developed against Live 12.4 Lite).
- Python 3.12+ for the MCP server (see `requirements.txt`). Note: this is separate from Live's own embedded Python 3.11 interpreter, which runs the Remote Script — you don't need to touch that one.
- An MCP client: [Claude Desktop](https://claude.ai/download) or [Claude Code](https://claude.com/claude-code).
- Optional hardware: Akai APC40 Mk2, Akai MPD218, and/or an M-Audio Oxygen 49 keyboard.

## Project layout

```
AbletonMCP/
├── AbletonMCP/                 ← copy this folder into Ableton's Remote Scripts dir
│   ├── __init__.py
│   ├── AbletonMCP.py           ← ControlSurface: TCP server + MIDI handling + command dispatch
│   ├── Server.py                ← TCP bridge thread (listens on :9877)
│   └── MidiMap.py               ← APC40 Mk2 / MPD218 / Oxygen 49 CC & note mappings
├── drum_patterns.py             ← preset pattern library + algorithmic generator
├── mcp_server.py                ← the MCP server exposing ableton_* tools to Claude
├── start_mcp_server.bat         ← convenience launcher (activates venv, runs server, tails the log)
├── requirements.txt
├── APC40_SETUP.md                ← deep-dive hardware/software setup guide for the APC40 Mk2
├── SETUP_SUMMARY.md              ← condensed setup + quick-test checklist
└── MPD218_Pro_Guide.pdf/.html    ← MPD218 hardware reference and mapping cheat sheet
```

## Setup

### 1. Install the Remote Script

Copy the `AbletonMCP/` folder to:

```
%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\
```

In Ableton: **Preferences → Link/MIDI** → set **Control Surface** to `AbletonMCP`, and set **Input**/**Output** to your controller (APC40 Mk2 / MPD218 / Oxygen 49) if you have one. Restart Live. You should see this in Live's log:

```
AbletonMCP v2.0 (APC40 Mk2 ready) — TCP 9877
```

### 2. Set up the MCP server environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Point your MCP client at `mcp_server.py`

**Claude Code** — add a `.mcp.json` in the project root (this file is git-ignored here since it bakes in an absolute local path — create your own):

```json
{
  "mcpServers": {
    "ableton": {
      "command": "<absolute-path-to-repo>/.venv/Scripts/python.exe",
      "args": ["<absolute-path-to-repo>/mcp_server.py"]
    }
  }
}
```

Restart Claude Code (or run `/mcp`) to pick up the new server.

**Claude Desktop** — add the same block to `%APPDATA%\Claude\claude_desktop_config.json`.

### 4. Run it

With Ableton open and the AbletonMCP control surface selected (port 9877 is already listening at that point), either let your MCP client spawn `mcp_server.py` automatically, or start it by hand for debugging:

```bash
start_mcp_server.bat
```

This activates the venv, runs the server with its log streamed to the console, and on exit tails the last 60 lines of `mcp_server.log`.

### 5. Try it

Ask Claude things like:

- "Get session info"
- "Create a MIDI track, name it Bass, and set its volume to 0.8"
- "Generate a funk drum pattern on track 0, slot 0 at complexity 0.7 and launch it"
- "Use the bossa_nova preset on track 1, slot 2"
- "Act as my drummer — read what I'm playing on the keyboard and create a matching pattern"
- "Map the full drum kit to the APC40 grid and create a clip"

## MCP tools reference

| Category | Tool | Description |
|---|---|---|
| Session / transport | `ableton_get_session_info` | Full snapshot: tempo, play state, tracks, clips, devices, scenes |
| | `ableton_play` / `ableton_stop` | Start / stop playback |
| | `ableton_set_tempo` | Set tempo in BPM (20–999) |
| Tracks | `ableton_create_midi_track` | Create a new MIDI track |
| | `ableton_get_track_info` | Full detail for one track: clips, devices, parameters |
| | `ableton_set_track_name` | Rename a track |
| | `ableton_set_track_volume` | Set volume (0.0 silent – 0.85 ≈ 0 dB – 1.0 = +6 dB) |
| | `ableton_set_track_pan` | Set pan (-1.0 to 1.0) |
| | `ableton_mute_track` / `ableton_solo_track` | Mute / solo a track |
| Clips | `ableton_create_clip` | Create an empty MIDI clip in a track slot |
| | `ableton_add_notes_to_clip` | Write MIDI notes into a clip (replaces existing notes) |
| | `ableton_set_clip_name` | Rename a clip |
| | `ableton_fire_clip` / `ableton_stop_clip` | Launch / stop a clip |
| Devices | `ableton_set_device_parameter` | Set a device parameter by index |
| AI drummer | `ableton_generate_drum_pattern` | Algorithmically generate a pattern (style, complexity, bars, swing, seed) |
| | `ableton_use_preset_pattern` | Apply a hand-crafted preset pattern |
| | `ableton_drummer_from_keyboard` | Infer a pattern from notes held on the Oxygen 49 and fire it |
| | `ableton_enable_auto_drummer` | Toggle the Remote Script's live auto-drummer flag |
| APC40 Mk2 | `ableton_apc40_get_active_pads` | Read currently pressed grid pads as `[row, col]` |
| | `ableton_apc40_pad_to_drum` | Map grid positions to GM drum notes (presets or explicit mapping) |
| | `ableton_apc40_sequence_from_grid` | Turn held pads into a playable step sequence |

GM drum pitches used by the clip tools: `36`=kick, `38`=snare, `42`=closed hat, `46`=open hat, `49`=crash, `51`=ride, `47`/`48`/`50`=toms.

## Hardware controller support

| Controller | Input | Mapped to |
|---|---|---|
| M-Audio Oxygen 49 | Transport CCs (22/21/23/24) | Play / Stop / Record / Loop |
| Akai MPD218 | 16 pads (ch. 10, GM notes) | Direct drum input |
| Akai MPD218 | Knobs 1–6 | Track volumes for tracks 1–6 |
| Akai APC40 Mk2 | 8×8 pad grid (notes 36–99) | Direct drum input via `ableton_apc40_*` tools |
| Akai APC40 Mk2 | 9 vertical faders (CC 48–56) | Track volumes + master |
| Akai APC40 Mk2 | 8 rotary knobs (CC 16–23) | Assignable controls |
| Akai APC40 Mk2 | Shift / Bank buttons | Navigation and mode selection |

Oxygen 49 transport CC numbers vary by firmware — if buttons don't respond, update `OXYGEN49_TRANSPORT_CCS` in `AbletonMCP/MidiMap.py`. See `APC40_SETUP.md` and `MPD218_Pro_Guide.pdf` for full hardware setup walkthroughs.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Cannot reach Ableton on port 9877" | Restart Live; confirm `AbletonMCP` is selected as the Control Surface in Preferences → Link/MIDI |
| Claude Code doesn't see the `ableton_*` tools | Add/verify `.mcp.json`, then restart the session or run `/mcp` |
| APC40 pads don't respond | Check the MIDI channel (should be channel 1 / 0-indexed 0) in Ableton's MIDI preferences |
| No LED feedback on APC40 pads | Set the Output port for the APC40 in Ableton's MIDI preferences |
| MCP server won't start | Make sure the venv is activated and dependencies are installed: `.venv\Scripts\activate` then `pip install -r requirements.txt` |
| Wrong notes coming from APC40 pads | Verify `APC40_PAD_NOTE_BASE` in `AbletonMCP/MidiMap.py` |

## Files not tracked in this repo

`.gitignore` excludes machine-specific and generated files so the repo stays portable:

- `.venv/`, `__pycache__/` — local Python environment and bytecode
- `.mcp.json` — bakes in an absolute local path to this machine's venv; create your own from the template above
- `.claude/` — local Claude Code permission grants, specific to one machine
- `mcp_server.log` — runtime log
- `generated-images/` — local scratch output
- `current.txt` — a personal working note, not project documentation
