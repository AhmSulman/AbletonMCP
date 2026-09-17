# AbletonMCP + APC40 Mk2 Setup Complete ✅

Claude is now configured as your AI drummer with full Akai APC40 Mk2 integration.

## What Was Set Up

### 1. **MIDI Controller Support** ✅
- **Akai APC40 Mk2** (Primary) — 64 pads, 9 faders, 8 knobs
- **AKAI MPD218** (Legacy) — 16 pads, 6 knobs
- **M-Audio Oxygen 49** (Legacy) — 49 keys, transport controls, 8 knobs

### 2. **Ableton Remote Script (AbletonMCP)** ✅
Updated with APC40 support:
- **AbletonMCP.py** — Handles APC40 pad input, fader control, knob logging
- **MidiMap.py** — Complete APC40 Mk2 MIDI mappings
  - Grid: Notes 36–99 (8×8 layout)
  - Faders: CC 48–56 (master + 8 tracks)
  - Knobs: CC 16–23 (assignable)
  - Transport: Shift/Bank buttons

### 3. **MCP Server (Claude Integration)** ✅
Enhanced with APC40 tools:
- `ableton_apc40_get_active_pads` — Read currently pressed pads
- `ableton_apc40_pad_to_drum` — Map drums to grid (4 preset patterns)
- `ableton_apc40_sequence_from_grid` — Convert pads to playable clips

### 4. **Documentation** ✅
- **APC40_SETUP.md** — Comprehensive hardware/software setup guide
- **Updated readme.txt** — Quick reference for all controllers
- **start_mcp_server.bat** — One-click launcher script

---

## Quick Start (3 Steps)

### Step 1: Verify Remote Script Installation
```
Copy AbletonMCP/ folder to:
C:\Users\<username>\Documents\Ableton\User Library\Remote Scripts\
```
✅ Already at: `c:\Users\ahmed\Desktop\AbletonMCP\AbletonMCP\`

### Step 2: Configure Ableton
```
Ableton Live → Preferences → MIDI
- Control Surface: AbletonMCP
- Input: Akai APC40 Mk2
- Output: Akai APC40 Mk2
- Restart Ableton
```

### Step 3: Start MCP Server
```bash
Double-click: c:\Users\ahmed\Desktop\AbletonMCP\start_mcp_server.bat
```
Or manually:
```bash
cd C:\Users\ahmed\Desktop\AbletonMCP
.venv\Scripts\python mcp_server.py
```

---

## First Test Commands

### Test 1: Basic Session Control
```
User in Claude: "Get session info"
Expected: Returns current tempo, play state, list of tracks
```

### Test 2: APC40 Pad Input
```
1. Press some pads on APC40
2. Ask Claude: "Show me which pads I'm holding"
Expected: Returns grid coordinates [row, col] of pressed pads
```

### Test 3: Map Drums to Grid
```
User: "Map the full drum kit to the APC40"
Expected: Creates MIDI clip with drums assigned to pad positions
```

### Test 4: Generate Pattern
```
User: "Generate a funk drum pattern on track 0, clip 1"
Expected: AI-generated funk pattern fires automatically
```

---

## File Locations

| File | Purpose | Location |
|------|---------|----------|
| Remote Script | Ableton integration | `AbletonMCP/AbletonMCP.py` |
| MIDI Mappings | Controller config | `AbletonMCP/MidiMap.py` |
| MCP Server | Claude integration | `mcp_server.py` |
| Drum Patterns | Pattern library | `drum_patterns.py` |
| **Setup Guide** | **Full APC40 docs** | **APC40_SETUP.md** |
| Launcher | Quick start script | `start_mcp_server.bat` |

---

## APC40 Mk2 Hardware Reference

### 64 Pads (8×8 Grid)
```
Notes 56-63 ────────────────── Notes 48-55  (top)
Notes 40-47 ────────────────── Notes 32-39
Notes 24-31 ────────────────── Notes 16-23
Notes 8-15  ────────────────── Notes 0-7    (bottom)
```
- **MIDI Channel**: 1 (0-indexed: 0)
- **Note Range**: 36–99
- **Velocity**: 0–127 (pressure-sensitive)

### 9 Faders (Right Side)
- **CC 48**: Master volume
- **CC 49–56**: Track 1–8 volumes
- **Value Range**: 0–127

### 8 Rotary Knobs (Below Grid)
- **CC 16–23**: Knob 1–8
- **Type**: Endless rotation (no min/max)
- **Value Range**: 0–127

### Transport Buttons
- **Shift Button**: Hold for secondary functions
- **Bank Left/Right**: Navigate between clips/devices

---

## Claude Commands (APC40-Specific)

### Get Active Pads
```
"What pads am I currently pressing on the APC40?"
"Show me active pads"
"Get active pads"
```
**Returns**: List of `[row, col]` coordinates

### Map Drums to Grid
```
"Map the full drum kit to the grid"
"Map drums to the APC40"
"Setup full_drums pattern"
```
**Options**: 
- `full_drums` — 16 common drums
- `kick_snare_hats` — Basic drums only
- `toms` — All tom variations
- `cymbals` — Cymbals and hi-hats

### Create Sequence from Pads
```
"Turn the pads I'm holding into a clip"
"Create a sequence from active pads"
"Make a beat from grid input"
```
**Tempo divisions**: whole, half, quarter, eighth, sixteenth

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│         Claude / Claude Code            │
│         (AI Drummer & Engineer)         │
└────────────┬────────────────────────────┘
             │
             │ MCP Protocol (stdio)
             ↓
┌─────────────────────────────────────────┐
│    mcp_server.py (MCP Server)           │
│  • ableton_apc40_get_active_pads       │
│  • ableton_apc40_pad_to_drum           │
│  • ableton_apc40_sequence_from_grid    │
│  • 20+ other Ableton tools             │
└────────────┬────────────────────────────┘
             │
             │ TCP JSON (localhost:9877)
             ↓
┌─────────────────────────────────────────┐
│  AbletonMCP.py (Remote Script)          │
│  • Receives commands from MCP server   │
│  • Dispatches to Ableton Live API      │
│  • MIDI input routing (APC40, MPD, O49)│
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│    Ableton Live 12.4 Lite               │
│  • Session state                       │
│  • Track & clip management             │
│  • Device control                      │
│  • MIDI input/output                   │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│    APC40 Mk2 (USB MIDI)                 │
│  • 64 pads (input)                     │
│  • 9 faders (input)                    │
│  • 8 knobs (input)                     │
│  • LED feedback (output)               │
└─────────────────────────────────────────┘
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot reach Ableton on port 9877" | Restart Ableton; ensure AbletonMCP is selected as Control Surface |
| APC40 pads don't respond | Check MIDI channel in Ableton (Preferences → MIDI) |
| No LED feedback on pads | Configure Output port in Ableton Preferences |
| MCP server won't start | Ensure venv is activated: `.venv\Scripts\activate.bat` |
| Pads send wrong notes | Verify `APC40_PAD_NOTE_BASE = 36` in MidiMap.py |

See **APC40_SETUP.md** for detailed troubleshooting.

---

## Next Steps

1. ✅ **Setup Complete** — All files configured
2. **Run** — Start `start_mcp_server.bat` with Ableton open
3. **Test** — Press APC40 pads and ask Claude questions
4. **Explore** — Try different patterns and workflows
5. **Extend** (Optional) — Add custom drum maps or knob assignments

---

## Key Features Summary

### ✅ Session Control
- Get/set tempo, play state, loop
- Create/manage tracks and clips
- Solo/mute/pan tracks
- Set device parameters

### ✅ Algorithmic Drumming
- 7 drum styles: rock, pop, funk, jazz, trap, reggae, half_time
- Complexity control (0.0–1.0)
- Swing and bar length options
- 8 hand-crafted preset patterns

### ✅ Grid Input (APC40)
- 64-pad grid (8×8) for drum input
- Automatic pad state tracking
- Map drums to any grid layout
- Convert pressed pads to playable sequences

### ✅ Hardware Control
- 9 faders for track volumes
- 8 knobs for assignable parameters
- Shift/Bank buttons for navigation
- Real-time MIDI monitoring

---

## Support

**Setup Guide**: See `APC40_SETUP.md`  
**MidiMap Reference**: See `AbletonMCP/MidiMap.py`  
**Drum Patterns**: See `drum_patterns.py`  
**MCP Tools**: See `mcp_server.py`

---

**Status**: 🟢 Production Ready (APC40 Mk2)  
**Version**: 2.0  
**Last Updated**: 2026-06-06
