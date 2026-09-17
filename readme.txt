What was built

AbletonMCP/
├── AbletonMCP/             ← copy this folder into Ableton's Remote Scripts
│   ├── __init__.py
│   ├── AbletonMCP.py       ← main ControlSurface (TCP server + MIDI handling)
│   ├── Server.py           ← TCP bridge thread (port 9877)
│   └── MidiMap.py          ← MPD218 + Oxygen 49 CC/note mappings
├── drum_patterns.py        ← 8 preset patterns + algorithmic generator
├── mcp_server.py           ← MCP server (Claude's tools)
└── requirements.txt
Setup (3 steps)
1. Install the Remote Script

Copy the AbletonMCP/ folder to:


%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\
Then in Live → Preferences → MIDI, set Control Surface to AbletonMCP, input to your MPD218/Oxygen 49.

2. Configure Claude

Add to %APPDATA%\Claude\claude_desktop_config.json:


{
  "mcpServers": {
    "ableton": {
      "command": "C:/Users/ahmed/Desktop/AbletonMCP/.venv/Scripts/python.exe",
      "args": ["C:/Users/ahmed/Desktop/AbletonMCP/mcp_server.py"]
    }
  }
}
3. Use it

Ask Claude things like:

"Generate a funk drum pattern on track 0, slot 0 at complexity 0.7 and launch it"
"Set tempo to 95 BPM"
"Use the bossa_nova preset on track 1 slot 2"
"Act as my drummer — read what I'm playing on the keyboard and create a matching pattern"
MIDI controllers (out of the box)
Controller	Action
Oxygen 49 transport	Play/Stop/Record/Loop (CCs 22/21/23/24)
MPD218 pads	Direct drum input (GM notes, ch10)
MPD218 knobs 1–6	Track volumes for tracks 1–6
APC40 Mk2 (new!)
  – 8×8 pad grid	Direct drum input via notes (36–99)
  – 9 vertical faders	Track volumes + master fader (CC 48–56)
  – 8 rotary knobs	Assignable controls (CC 16–23)
  – Shift/Bank buttons	Navigation and mode selection

APC40 Mk2 Claude Tools
Ask Claude:
  "Get all active pads on the APC40"
  "Map the full drum kit to the APC40 grid and create a clip"
  "Create a sequence from the pads I'm currently holding"

Note: Oxygen 49 transport CC numbers vary by firmware. If buttons don't work, update OXYGEN49_TRANSPORT_CCS in AbletonMCP/MidiMap.py