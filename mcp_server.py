"""
AbletonMCP — MCP server (enhanced drummer edition)

Communicates with the AbletonMCP Remote Script via TCP on localhost:9877,
using the same JSON protocol as the `ableton-mcp` PyPI package so the two
are interchangeable.

Run:
  .venv\\Scripts\\python mcp_server.py

Add to Claude Desktop config (%APPDATA%\\Claude\\claude_desktop_config.json):
  {
    "mcpServers": {
      "ableton": {
        "command": "<path-to-repo>/.venv/Scripts/python.exe",
        "args":    ["<path-to-repo>/mcp_server.py"]
      }
    }
  }

Or for Claude Code (.claude/settings.json or via /mcp add):
  "ableton": {
    "command": "<path-to-repo>/.venv/Scripts/python.exe",
    "args":    ["<path-to-repo>/mcp_server.py"]
  }
"""

import asyncio
import json
import logging
import socket
import sys
import time
import traceback
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

sys.path.insert(0, str(Path(__file__).parent))
from drum_patterns import (
    generate_pattern,
    get_pattern,
    guess_style_from_notes,
    list_patterns,
)

ABLETON_HOST = "127.0.0.1"
ABLETON_PORT = 9877

# ---------------------------------------------------------------------------
# Logging — goes to stderr (visible in the .bat console) and mcp_server.log.
# NEVER log to stdout: the MCP stdio protocol owns it and any stray text
# there corrupts the JSON-RPC stream to Claude.
# ---------------------------------------------------------------------------
LOG_FILE = Path(__file__).parent / "mcp_server.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("ableton-mcp")


def _trunc(text: str, limit: int = 2000) -> str:
    """Keep huge payloads (e.g. session snapshots) from flooding the log."""
    return text if len(text) <= limit else f"{text[:limit]}... [{len(text)} chars total]"

# APC40 Mk2 pad-to-drum mappings (row, col) → GM pitch
APC40_DRUM_MAPS = {
    "kick_snare_hats": {
        (0, 0): 36,  # kick
        (0, 1): 38,  # snare
        (0, 2): 42,  # closed hat
        (0, 3): 46,  # open hat
    },
    "full_drums": {
        (0, 0): 36, (0, 1): 38, (0, 2): 42, (0, 3): 46,  # Kick, Snare, Closed Hat, Open Hat
        (1, 0): 37, (1, 1): 40, (1, 2): 44, (1, 3): 49,  # Side Stick, Electric Snare, Pedal Hat, Crash
        (2, 0): 51, (2, 1): 50, (2, 2): 48, (2, 3): 47,  # Ride, High Tom, Hi-Mid Tom, Low-Mid Tom
        (3, 0): 43, (3, 1): 45, (3, 2): 41, (3, 3): 35,  # High Floor Tom, Low Tom, Low Floor Tom, Bass Drum
    },
    "toms": {
        (0, 0): 50, (0, 1): 48, (0, 2): 47, (0, 3): 43,  # High, Hi-Mid, Low-Mid, Low Tom
    },
    "cymbals": {
        (0, 0): 42, (0, 1): 44, (0, 2): 46, (0, 3): 49,  # Closed Hat, Pedal Hat, Open Hat, Crash
        (1, 0): 51, (1, 1): 55, (1, 2): 57, (1, 3): 59,  # Ride, Splash, Crash 2, Ride 2
    },
}

app = Server("ableton-mcp")


# ---------------------------------------------------------------------------
# TCP bridge to the Remote Script
# ---------------------------------------------------------------------------

def _send_command_sync(cmd_type: str, params: dict | None = None) -> dict:
    """Blocking TCP call (run in a thread to keep asyncio happy)."""
    payload = json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8")
    log.info("TCP -> %s:%s  command=%r", ABLETON_HOST, ABLETON_PORT, cmd_type)
    log.debug("TCP -> payload: %s", _trunc(payload.decode("utf-8")))
    t0 = time.monotonic()
    buf = b""
    try:
        with socket.create_connection((ABLETON_HOST, ABLETON_PORT), timeout=15) as sock:
            log.debug("TCP connected (local port %s)", sock.getsockname()[1])
            sock.sendall(payload)
            log.debug("TCP sent %d bytes, waiting for response...", len(payload))
            sock.settimeout(15)
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    log.warning("TCP connection closed by Ableton after %d bytes", len(buf))
                    break
                buf += chunk
                log.debug("TCP recv %d bytes (total %d)", len(chunk), len(buf))
                try:
                    response = json.loads(buf.decode("utf-8"))
                except json.JSONDecodeError:
                    continue  # response not complete yet, keep reading
                elapsed = (time.monotonic() - t0) * 1000
                log.info("TCP <- response for %r in %.0f ms, status=%r",
                         cmd_type, elapsed, response.get("status"))
                log.debug("TCP <- body: %s", _trunc(json.dumps(response)))
                return response
    except ConnectionRefusedError:
        log.error("TCP connection REFUSED at %s:%s — is Ableton running with the "
                  "AbletonMCP control surface enabled?", ABLETON_HOST, ABLETON_PORT)
        raise
    except socket.timeout:
        log.error("TCP TIMEOUT after 15s for command %r (partial data: %d bytes)",
                  cmd_type, len(buf))
        raise
    except OSError as exc:
        log.error("TCP socket error for command %r: %s", cmd_type, exc)
        raise
    raise RuntimeError("Connection closed without a complete JSON response")


async def _call(cmd_type: str, params: dict | None = None) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_command_sync, cmd_type, params)


def _ok(response: dict) -> dict:
    """Unwrap the result field; raise on error status."""
    if response.get("status") == "error":
        log.error("Ableton returned error status: %s", response.get("message"))
        raise RuntimeError(response.get("message", "Unknown error from Ableton"))
    return response.get("result", {})


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    log.info("MCP client requested tool list")
    presets = ", ".join(list_patterns())
    return [
        # ── session / transport ─────────────────────────────────────────
        Tool(
            name="ableton_get_session_info",
            description=(
                "Return a full snapshot of the Ableton session: tempo, "
                "play state, all tracks (name, type, clips, devices), scenes."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="ableton_get_track_info",
            description="Get full detail for one track: clips, devices and device parameters.",
            inputSchema={
                "type": "object",
                "properties": {"track_index": {"type": "integer"}},
                "required": ["track_index"],
            },
        ),
        Tool(
            name="ableton_play",
            description="Start or resume playback.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="ableton_stop",
            description="Stop playback.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="ableton_set_tempo",
            description="Set session tempo in BPM.",
            inputSchema={
                "type": "object",
                "properties": {"bpm": {"type": "number", "description": "20–999"}},
                "required": ["bpm"],
            },
        ),
        # ── tracks ─────────────────────────────────────────────────────
        Tool(
            name="ableton_create_midi_track",
            description="Create a new MIDI track. -1 appends it at the end.",
            inputSchema={
                "type": "object",
                "properties": {"index": {"type": "integer", "description": "Insert position, -1 = end"}},
                "required": [],
            },
        ),
        Tool(
            name="ableton_set_track_name",
            description="Rename a track.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "name":        {"type": "string"},
                },
                "required": ["track_index", "name"],
            },
        ),
        Tool(
            name="ableton_set_track_volume",
            description="Set track volume. 0.0=silent, 0.85≈0 dB, 1.0=+6 dB.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "volume":      {"type": "number", "description": "0.0–1.0"},
                },
                "required": ["track_index", "volume"],
            },
        ),
        Tool(
            name="ableton_set_track_pan",
            description="Set track panning. -1=full left, 0=center, 1=full right.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "pan":         {"type": "number", "description": "-1.0 to 1.0"},
                },
                "required": ["track_index", "pan"],
            },
        ),
        Tool(
            name="ableton_mute_track",
            description="Mute or unmute a track.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "mute":        {"type": "boolean"},
                },
                "required": ["track_index", "mute"],
            },
        ),
        Tool(
            name="ableton_solo_track",
            description="Solo or unsolo a track.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "solo":        {"type": "boolean"},
                },
                "required": ["track_index", "solo"],
            },
        ),
        # ── clips ──────────────────────────────────────────────────────
        Tool(
            name="ableton_create_clip",
            description="Create an empty MIDI clip in a track slot.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index":  {"type": "integer", "description": "Slot index"},
                    "length":      {"type": "number", "description": "Length in beats (4.0 = 1 bar)"},
                },
                "required": ["track_index", "clip_index"],
            },
        ),
        Tool(
            name="ableton_add_notes_to_clip",
            description=(
                "Write MIDI notes into a clip (replaces existing notes). "
                "Use GM drum pitches for drum tracks: "
                "36=kick, 38=snare, 42=closed hat, 46=open hat, "
                "49=crash, 51=ride, 47/48/50=toms."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index":  {"type": "integer"},
                    "notes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "pitch":      {"type": "integer"},
                                "start_time": {"type": "number", "description": "Start beat"},
                                "duration":   {"type": "number", "description": "Duration in beats"},
                                "velocity":   {"type": "integer", "description": "0–127"},
                                "mute":       {"type": "boolean"},
                            },
                            "required": ["pitch", "start_time", "duration"],
                        },
                    },
                },
                "required": ["track_index", "clip_index", "notes"],
            },
        ),
        Tool(
            name="ableton_set_clip_name",
            description="Rename a clip.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index":  {"type": "integer"},
                    "name":        {"type": "string"},
                },
                "required": ["track_index", "clip_index", "name"],
            },
        ),
        Tool(
            name="ableton_fire_clip",
            description="Launch/fire a clip.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index":  {"type": "integer"},
                },
                "required": ["track_index", "clip_index"],
            },
        ),
        Tool(
            name="ableton_stop_clip",
            description="Stop a clip.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index":  {"type": "integer"},
                },
                "required": ["track_index", "clip_index"],
            },
        ),
        # ── devices ────────────────────────────────────────────────────
        Tool(
            name="ableton_set_device_parameter",
            description=(
                "Set a device parameter value. Use ableton_get_track_info to "
                "discover device_index and param_index for a track."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index":  {"type": "integer"},
                    "device_index": {"type": "integer", "description": "Default 0"},
                    "param_index":  {"type": "integer"},
                    "value":        {"type": "number"},
                },
                "required": ["track_index", "param_index", "value"],
            },
        ),
        # ── AI drummer ─────────────────────────────────────────────────
        Tool(
            name="ableton_generate_drum_pattern",
            description=(
                "Be the drummer: algorithmically generate a drum pattern and "
                "write it into a clip slot. Optionally fire it immediately. "
                "Styles: rock, pop, funk, jazz, trap, reggae, half_time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index":  {"type": "integer"},
                    "style": {
                        "type": "string",
                        "enum": ["rock", "pop", "funk", "jazz", "trap", "reggae", "half_time"],
                    },
                    "complexity": {"type": "number", "description": "0.0–1.0, default 0.5"},
                    "bars":       {"type": "integer", "description": "Loop bars (1–8), default 1"},
                    "swing":      {"type": "boolean"},
                    "seed":       {"type": "integer", "description": "RNG seed for reproducibility"},
                    "launch":     {"type": "boolean", "description": "Fire clip after writing"},
                },
                "required": ["track_index", "clip_index", "style"],
            },
        ),
        Tool(
            name="ableton_use_preset_pattern",
            description=f"Apply a hand-crafted preset pattern. Available: {presets}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index":  {"type": "integer"},
                    "clip_index":   {"type": "integer"},
                    "pattern_name": {"type": "string", "description": f"One of: {presets}"},
                    "launch":       {"type": "boolean"},
                },
                "required": ["track_index", "clip_index", "pattern_name"],
            },
        ),
        Tool(
            name="ableton_drummer_from_keyboard",
            description=(
                "Read the notes currently held on the Oxygen 49 keyboard, "
                "infer a drum style from the chord/interval content, generate "
                "a matching pattern, and fire it. This is the live auto-drummer."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index":  {"type": "integer"},
                    "complexity":  {"type": "number", "description": "0.0–1.0"},
                    "bars":        {"type": "integer"},
                    "launch":      {"type": "boolean", "description": "Default true"},
                },
                "required": ["track_index", "clip_index"],
            },
        ),
        Tool(
            name="ableton_enable_auto_drummer",
            description="Enable/disable the Remote Script's auto-drummer flag.",
            inputSchema={
                "type": "object",
                "properties": {"enabled": {"type": "boolean"}},
                "required": ["enabled"],
            },
        ),
        # ── APC40 Mk2 control ─────────────────────────────────────────
        Tool(
            name="ableton_apc40_get_active_pads",
            description=(
                "Get all currently pressed pads on the APC40 Mk2 grid as "
                "[row, col] coordinates. Useful for reading live input."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="ableton_apc40_pad_to_drum",
            description=(
                "Map APC40 Mk2 grid positions directly to drum notes. "
                "Specify a pattern like 'kick' (bottom-left), 'snare' (bottom-right), etc., "
                "or provide explicit [row, col] → GM pitch mappings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Quick preset: 'kick_snare_hats', 'full_drums', 'toms', etc.",
                    },
                    "track_index": {"type": "integer"},
                    "clip_index": {"type": "integer"},
                    "launch": {"type": "boolean", "description": "Fire the clip after mapping"},
                },
                "required": ["track_index", "clip_index"],
            },
        ),
        Tool(
            name="ableton_apc40_sequence_from_grid",
            description=(
                "Convert currently held APC40 pads into a playable sequence. "
                "Each pressed pad becomes a note, ordered by position and timing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "track_index": {"type": "integer"},
                    "clip_index": {"type": "integer"},
                    "tempo_subdivision": {
                        "type": "string",
                        "enum": ["whole", "half", "quarter", "eighth", "sixteenth"],
                        "description": "Time between pads (default: sixteenth)",
                    },
                    "launch": {"type": "boolean"},
                },
                "required": ["track_index", "clip_index"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("MCP tool call: %s  args=%s", name, _trunc(json.dumps(arguments)))
    t0 = time.monotonic()
    try:
        result = await _execute(name, arguments)
    except ConnectionRefusedError:
        result = {
            "error": (
                "Cannot reach Ableton on port 9877. "
                "Select 'AbletonMCP' as a Control Surface in "
                "Live → Preferences → MIDI and restart Ableton."
            )
        }
    except Exception as exc:
        log.error("Tool %s failed: %s\n%s", name, exc, traceback.format_exc())
        result = {"error": str(exc)}
    elapsed = (time.monotonic() - t0) * 1000
    log.info("MCP tool result for %s in %.0f ms: %s",
             name, elapsed, _trunc(json.dumps(result)))
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _execute(name: str, args: dict) -> dict:

    # ── session / transport ────────────────────────────────────────────
    if name == "ableton_get_session_info":
        return _ok(await _call("get_session_info"))

    if name == "ableton_get_track_info":
        return _ok(await _call("get_track_info", {"track_index": args["track_index"]}))

    if name == "ableton_play":
        return _ok(await _call("start_playback"))

    if name == "ableton_stop":
        return _ok(await _call("stop_playback"))

    if name == "ableton_set_tempo":
        return _ok(await _call("set_tempo", {"tempo": args["bpm"]}))

    # ── tracks ─────────────────────────────────────────────────────────
    if name == "ableton_create_midi_track":
        return _ok(await _call("create_midi_track", {"index": args.get("index", -1)}))

    if name == "ableton_set_track_name":
        return _ok(await _call("set_track_name", args))

    if name == "ableton_set_track_volume":
        return _ok(await _call("set_track_volume", args))

    if name == "ableton_set_track_pan":
        return _ok(await _call("set_track_pan", args))

    if name == "ableton_mute_track":
        return _ok(await _call("mute_track", args))

    if name == "ableton_solo_track":
        return _ok(await _call("solo_track", args))

    # ── clips ──────────────────────────────────────────────────────────
    if name == "ableton_create_clip":
        return _ok(await _call("create_clip", {
            "track_index": args["track_index"],
            "clip_index":  args["clip_index"],
            "length":      args.get("length", 4.0),
        }))

    if name == "ableton_add_notes_to_clip":
        return _ok(await _call("add_notes_to_clip", args))

    if name == "ableton_set_clip_name":
        return _ok(await _call("set_clip_name", args))

    if name == "ableton_fire_clip":
        return _ok(await _call("fire_clip", args))

    if name == "ableton_stop_clip":
        return _ok(await _call("stop_clip", args))

    # ── devices ────────────────────────────────────────────────────────
    if name == "ableton_set_device_parameter":
        return _ok(await _call("set_device_parameter", args))

    # ── AI drummer ─────────────────────────────────────────────────────
    if name == "ableton_generate_drum_pattern":
        notes = generate_pattern(
            style=args.get("style", "rock"),
            complexity=float(args.get("complexity", 0.5)),
            bars=int(args.get("bars", 1)),
            swing=bool(args.get("swing", False)),
            seed=args.get("seed"),
        )
        length = int(args.get("bars", 1)) * 4.0
        # Create clip then write notes
        await _call("create_clip", {
            "track_index": args["track_index"],
            "clip_index":  args["clip_index"],
            "length":      length,
        })
        # Convert to start_time key expected by Remote Script
        wire_notes = [
            {**{k: v for k, v in n.items() if k != "time"},
             "start_time": n["time"]}
            for n in notes
        ]
        result = _ok(await _call("add_notes_to_clip", {
            "track_index": args["track_index"],
            "clip_index":  args["clip_index"],
            "notes":       wire_notes,
        }))
        if args.get("launch"):
            await _call("fire_clip", {
                "track_index": args["track_index"],
                "clip_index":  args["clip_index"],
            })
        return {**result, "style": args.get("style"), "notes_generated": len(notes)}

    if name == "ableton_use_preset_pattern":
        notes = get_pattern(args["pattern_name"])
        last_end = max(n["time"] + n["duration"] for n in notes)
        length = max(1, round(last_end / 4.0)) * 4.0
        await _call("create_clip", {
            "track_index": args["track_index"],
            "clip_index":  args["clip_index"],
            "length":      length,
        })
        wire_notes = [
            {**{k: v for k, v in n.items() if k != "time"},
             "start_time": n["time"]}
            for n in notes
        ]
        result = _ok(await _call("add_notes_to_clip", {
            "track_index": args["track_index"],
            "clip_index":  args["clip_index"],
            "notes":       wire_notes,
        }))
        if args.get("launch"):
            await _call("fire_clip", {
                "track_index": args["track_index"],
                "clip_index":  args["clip_index"],
            })
        return {**result, "pattern": args["pattern_name"]}

    if name == "ableton_drummer_from_keyboard":
        kb_result = _ok(await _call("get_keyboard_notes"))
        held: list[int] = kb_result.get("notes", [])
        style = guess_style_from_notes(held)
        notes = generate_pattern(
            style=style,
            complexity=float(args.get("complexity", 0.5)),
            bars=int(args.get("bars", 1)),
        )
        length = int(args.get("bars", 1)) * 4.0
        await _call("create_clip", {
            "track_index": args["track_index"],
            "clip_index":  args["clip_index"],
            "length":      length,
        })
        wire_notes = [
            {**{k: v for k, v in n.items() if k != "time"},
             "start_time": n["time"]}
            for n in notes
        ]
        result = _ok(await _call("add_notes_to_clip", {
            "track_index": args["track_index"],
            "clip_index":  args["clip_index"],
            "notes":       wire_notes,
        }))
        if args.get("launch", True):
            await _call("fire_clip", {
                "track_index": args["track_index"],
                "clip_index":  args["clip_index"],
            })
        return {
            **result,
            "detected_notes":  held,
            "chosen_style":    style,
            "notes_generated": len(notes),
        }

    if name == "ableton_enable_auto_drummer":
        return _ok(await _call("enable_auto_drummer", args))

    # ── APC40 Mk2 ──────────────────────────────────────────────────────
    if name == "ableton_apc40_get_active_pads":
        return _ok(await _call("get_apc40_active_pads"))

    if name == "ableton_apc40_pad_to_drum":
        pattern_name = args.get("pattern", "full_drums")
        pad_map = APC40_DRUM_MAPS.get(pattern_name, APC40_DRUM_MAPS["full_drums"])
        notes = []
        for (row, col), pitch in pad_map.items():
            notes.append({
                "pitch": pitch,
                "start_time": 0.0,
                "duration": 0.5,
                "velocity": 80,
            })
        length = 4.0
        await _call("create_clip", {
            "track_index": args["track_index"],
            "clip_index": args["clip_index"],
            "length": length,
        })
        result = _ok(await _call("add_notes_to_clip", {
            "track_index": args["track_index"],
            "clip_index": args["clip_index"],
            "notes": notes,
        }))
        if args.get("launch"):
            await _call("fire_clip", {
                "track_index": args["track_index"],
                "clip_index": args["clip_index"],
            })
        return {**result, "pattern": pattern_name, "notes_mapped": len(notes)}

    if name == "ableton_apc40_sequence_from_grid":
        active = _ok(await _call("get_apc40_active_pads"))
        pads = active.get("active_pads", [])
        if not pads:
            return {"error": "No pads pressed on APC40"}
        # Sort pads by row then col, map each to a note
        pads.sort(key=lambda p: (p["row"], p["col"]))
        subdivision_map = {
            "whole": 4.0,
            "half": 2.0,
            "quarter": 1.0,
            "eighth": 0.5,
            "sixteenth": 0.25,
        }
        step = subdivision_map.get(args.get("tempo_subdivision", "sixteenth"), 0.25)
        notes = []
        for i, pad in enumerate(pads):
            # Map pad grid position to note pitch
            note = pad["note"]
            notes.append({
                "pitch": note,
                "start_time": i * step,
                "duration": step * 0.8,
                "velocity": 100,
            })
        length = max(1, (len(notes) * step + 1.0))
        await _call("create_clip", {
            "track_index": args["track_index"],
            "clip_index": args["clip_index"],
            "length": length,
        })
        result = _ok(await _call("add_notes_to_clip", {
            "track_index": args["track_index"],
            "clip_index": args["clip_index"],
            "notes": notes,
        }))
        if args.get("launch", True):
            await _call("fire_clip", {
                "track_index": args["track_index"],
                "clip_index": args["clip_index"],
            })
        return {**result, "sequence_length": len(notes), "duration": length}

    return {"error": f"Unknown tool: {name!r}"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    log.info("=" * 60)
    log.info("AbletonMCP server starting (python %s)", sys.version.split()[0])
    log.info("Ableton bridge target: %s:%s | log file: %s",
             ABLETON_HOST, ABLETON_PORT, LOG_FILE)
    log.info("Waiting for MCP client (Claude) on stdio...")
    async with stdio_server() as (read_stream, write_stream):
        log.info("MCP stdio streams open, running server")
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server stopped by user (Ctrl+C)")
    except Exception:
        log.critical("Server crashed:\n%s", traceback.format_exc())
        raise
