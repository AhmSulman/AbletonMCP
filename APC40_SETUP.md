# AbletonMCP + Akai APC40 Mk2 Setup Guide

Claude as your AI drummer with the APC40 Mk2 controller.

## Hardware Setup

### APC40 Mk2 Configuration
1. **Connect to Computer**: USB connection (bus power included)
2. **MIDI Channel**: Configure to send/receive on **Channel 1** (0-indexed: 0)
   - Factory default is usually correct
   - If needed, hold Setup button on device to access settings

### Ableton Live Configuration
1. **Open Preferences** → **MIDI**
2. Set **Control Surface** to `AbletonMCP`
3. **Input Port**: Select your APC40 device
4. **Output Port**: Select your APC40 device (for pad feedback LEDs)
5. Click OK and restart Ableton Live

### Test Connection
In Live, press a pad on the APC40. You should see activity in the Log window:
```
AbletonMCP v2.0 (APC40 Mk2 ready) — TCP 9877
APC40 pad [0,0] (note 36) — pressed
```

## Software Setup

### 1. Install MCP Server

The venv is already set up with dependencies:
```bash
cd C:\Users\ahmed\Desktop\AbletonMCP
.venv\Scripts\python mcp_server.py
```

### 2. Configure Claude Code / Claude Desktop

**Option A: Claude Code (Recommended)**
```bash
# In your Claude Code workspace root:
.claude/settings.json
```

Add to `mcpServers`:
```json
{
  "mcpServers": {
    "ableton": {
      "command": "C:/Users/ahmed/Desktop/AbletonMCP/.venv/Scripts/python.exe",
      "args":    ["C:/Users/ahmed/Desktop/AbletonMCP/mcp_server.py"]
    }
  }
}
```

**Option B: Claude Desktop**
```
%APPDATA%\Claude\claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "ableton": {
      "command": "C:/Users/ahmed/Desktop/AbletonMCP/.venv/Scripts/python.exe",
      "args":    ["C:/Users/ahmed/Desktop/AbletonMCP/mcp_server.py"]
    }
  }
}
```

Restart Claude to load the MCP server.

## APC40 Mk2 Hardware Reference

### 64-Pad Grid (8×8)
- **Location**: Main control surface
- **MIDI Channel**: 1 (0-indexed: 0)
- **Note Range**: 36–99 (C1–G6)
- **Layout**:
  ```
  63  62  61  60  59  58  57  56  (top)
  55  54  53  52  51  50  49  48
  47  46  45  44  43  42  41  40
  39  38  37  36  35  34  33  32
  31  30  29  28  27  26  25  24
  23  22  21  20  19  18  17  16
  15  14  13  12  11  10   9   8
   7   6   5   4   3   2   1   0  (bottom)
  ```
- **Velocity**: 0–127 (pressure-sensitive on Mk2)
- **Colors**: RGB LED feedback (if configured in Ableton)

### 9 Vertical Faders
- **MIDI CC**: 48–56
  - CC 48: Master volume
  - CC 49–56: Track volumes 1–8
- **Range**: 0–127
- **Position**: Right side of device

### 8 Rotary Knobs
- **MIDI CC**: 16–23
- **Type**: Endless rotary (no min/max)
- **Below the grid**: Assignable to any parameter
- **Range**: 0–127

### Transport/Control Buttons
- **Shift Button** (Shift): Hold to access secondary functions
- **Bank Left/Right**: Navigate clips/devices
- **Device/Clip/Master Buttons**: Mode selection

## Claude Commands Reference

### Get Session Info
```
"What's playing? Get session info"
```
Returns tempo, tracks, clips, scenes, and play state.

### APC40 Pad Mapping (New!)
```
"Map the full drum kit to the APC40 grid"
```
Creates a clip with drum sounds mapped to grid positions:
- **full_drums**: All 16 common drums (kick, snare, hats, toms, cymbals)
- **kick_snare_hats**: Basic drums only
- **toms**: All tom variations
- **cymbals**: Cymbals and hi-hats

### Get Active Pads
```
"Show me which pads I'm holding on the APC40"
```
Returns currently pressed pad coordinates `[row, col]`.

### Create Sequence from Grid
```
"Create a drum sequence from the pads I'm playing"
```
Converts held pads into a playable clip. Each pad becomes a note in order of position.

### Generate Drum Pattern
```
"Generate a funk pattern on track 0, clip slot 1 at complexity 0.7"
```
AI-generated patterns: rock, pop, funk, jazz, trap, reggae, half_time.

### Manual Fader/Knob Control
The APC40 faders automatically control track volumes (no Claude command needed).
- **Faders 1–8**: Track 1–8 volumes
- **Faders 0 (Master)**: Ready for custom mapping
- **Knobs 1–8**: Currently log-only; can be mapped to device parameters via Claude

## Typical Workflow

### Live Session with Pad Input
1. **Open Ableton** → select AbletonMCP as Control Surface
2. **Create MIDI track** with drum plugin (e.g., Drums)
3. **In Claude**:
   ```
   "Create a MIDI clip on track 0, slot 0 with a rock drum pattern"
   ```
4. **Press APC40 pads** during playback to hear the mapped drums
5. **Ask Claude to adjust**:
   ```
   "Increase the tempo to 95 BPM"
   "Mute track 1 (bass)"
   ```

### AI Drummer Mode
1. **Play notes on a keyboard** track (or hold Oxygen 49 keys)
2. **Ask Claude**:
   ```
   "Read the keyboard and auto-generate a matching drum pattern"
   ```
3. Claude analyzes the held notes and creates a suitable pattern

### Grid Sequencer
1. **Hold multiple APC40 pads**
2. **Ask Claude**:
   ```
   "Turn the pads I'm holding into a sequence"
   ```
3. Pads are converted to a playable clip in order of position

## Troubleshooting

### No MIDI input from APC40
- **Check**: AbletonMCP is selected as Control Surface in Preferences
- **Check**: USB cable is connected
- **Check**: Ableton has been restarted after setting Control Surface
- **Monitor**: Live → View → MIDI → Monitor to see raw MIDI data

### LEDs don't light up on pads
- **Check**: Output port is configured in Preferences
- **Note**: LED feedback requires Ableton to send data back to the device
- **Workaround**: Pads still work for input even without LED feedback

### Claude can't reach Ableton
- **Check**: Ableton is running and Remote Script is active
- **Check**: Port 9877 is not blocked by firewall
- **Check**: MCP server is running (`python mcp_server.py`)
- **Error message**: "Cannot reach Ableton on port 9877" appears if connection fails

### APC40 sending notes to wrong channel
- **In MidiMap.py**, verify:
  ```python
  APC40_CHANNEL = 0  # MIDI channel 1 (0-indexed)
  APC40_PAD_NOTE_BASE = 36  # C1 (adjust if factory config differs)
  ```
- Use **MIDI monitor** in Live to check what notes are being sent

## Advanced Configuration

### Custom Pad Mappings
Edit `mcp_server.py`:
```python
APC40_DRUM_MAPS = {
    "my_custom_map": {
        (0, 0): 36,  # [row, col] → GM pitch
        (0, 1): 38,
        # ... add more mappings
    }
}
```
Then ask Claude:
```
"Map my_custom_map to the APC40 grid"
```

### Assign Knobs to Device Parameters
Currently, knobs 1–8 log their values. To control device parameters:
1. Identify device index and parameter index using:
   ```
   "Get info about track 0"
   ```
2. Ask Claude to create a persistent knob mapping
3. Requires extending the Remote Script (can be added on request)

## File Structure
```
AbletonMCP/
├── AbletonMCP/
│   ├── __init__.py
│   ├── AbletonMCP.py       ← Remote Script (add APC40 support)
│   ├── MidiMap.py          ← APC40 mappings defined here
│   └── Server.py           ← TCP bridge
├── drum_patterns.py        ← Pattern library
├── mcp_server.py           ← Claude MCP server (APC40 tools)
└── APC40_SETUP.md          ← This file
```

## Next Steps

1. ✅ Install and configure AbletonMCP Remote Script
2. ✅ Set up Claude MCP server
3. **Try it**:
   - Open Ableton + create a drum track
   - Ask Claude: "Get session info"
   - Press APC40 pads and ask: "Show active pads"
   - Create a pattern: "Generate a funk beat"

4. **Extend** (optional):
   - Add custom drum maps
   - Map knobs to device parameters
   - Create step sequencer interface on grid

---

**Version**: 2.0 (APC40 Mk2)  
**Last Updated**: 2026-06-06  
**Author**: Ahmed (Claude Code)
