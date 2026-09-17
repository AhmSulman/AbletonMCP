"""
AbletonMCP Remote Script — Live 12.4 Lite
Python 3.11 (Ableton's embedded interpreter)

Protocol: TCP JSON on localhost:9877
  in:  {"type": "<command>", "params": {...}}
  out: {"status": "ok",    "result": {...}}
     | {"status": "error", "message": "..."}

Compatible with the `ableton-mcp` PyPI package (ableton_mcp >= 1.0.4)
plus extra drummer / MPD218 / Oxygen-49 commands.

Install: copy the AbletonMCP/ folder to
  %USERPROFILE%/Documents/Ableton/User Library/Remote Scripts/
Then select "AbletonMCP" in Live -> Preferences -> MIDI -> Control Surface.
"""

import queue

from _Framework.ControlSurface import ControlSurface
from . import MidiMap
from .Server import start_server_thread

PUMP_INTERVAL = 1  # ticks (~1/30 s each)


class AbletonMCP(ControlSurface):

    def __init__(self, c_instance):
        super().__init__(c_instance)
        self._command_queue: queue.Queue = queue.Queue()
        self._active_keys: set[int] = set()
        self._auto_drummer = False
        self._apc40_pressed_pads: dict[int, bool] = {}  # Track APC40 pad states

        self._server_sock = start_server_thread(self._command_queue)
        self._schedule_pump()
        self.log_message("AbletonMCP v2.0 (APC40 Mk2 ready) — TCP 9877")

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def disconnect(self):
        try:
            self._server_sock.close()
        except Exception:
            pass
        super().disconnect()

    # ------------------------------------------------------------------ #
    # Command pump (Ableton main thread, ~30 Hz)                          #
    # ------------------------------------------------------------------ #

    def _schedule_pump(self):
        self.schedule_message(PUMP_INTERVAL, self._pump)

    def _pump(self):
        try:
            while not self._command_queue.empty():
                _cid, msg, response_q = self._command_queue.get_nowait()
                try:
                    result = self._dispatch(msg)
                    response_q.put({"status": "ok", "result": result})
                except Exception as exc:
                    response_q.put({"status": "error", "message": str(exc)})
        except Exception as exc:
            self.log_message(f"AbletonMCP pump error: {exc}")
        finally:
            self._schedule_pump()

    # ------------------------------------------------------------------ #
    # MIDI input                                                           #
    # ------------------------------------------------------------------ #

    def receive_midi(self, midi_bytes):
        if len(midi_bytes) < 3:
            return
        status, data1, data2 = midi_bytes[0], midi_bytes[1], midi_bytes[2]
        channel  = status & 0x0F
        msg_type = status & 0xF0

        # APC40 Mk2 pads: notes on channel 1 (note on/off)
        if channel == MidiMap.APC40_CHANNEL:
            if msg_type == 0x90 or msg_type == 0x80:
                self._handle_apc40_pad(data1, data2)
            # APC40 faders and knobs (CCs)
            elif msg_type == 0xB0:
                self._handle_apc40_cc(data1, data2)

        # Track Oxygen 49 keys for chord detection
        if channel == MidiMap.OXYGEN49_CHANNEL:
            if msg_type == 0x90 and data2 > 0:
                self._active_keys.add(data1)
            elif msg_type == 0x80 or (msg_type == 0x90 and data2 == 0):
                self._active_keys.discard(data1)
            # Transport CCs
            if msg_type == 0xB0 and data2 > 0:
                self._handle_oxygen_cc(data1)

        # MPD218 knobs → track volumes
        if channel == MidiMap.MPD218_KNOB_CHANNEL and msg_type == 0xB0:
            self._handle_mpd_knob(data1, data2)

    def _handle_oxygen_cc(self, cc: int):
        song  = self.song()
        trans = MidiMap.OXYGEN49_TRANSPORT_CCS
        if cc == trans["play"]:
            song.continue_playing()
        elif cc == trans["stop"]:
            song.stop_playing()
        elif cc == trans["record"]:
            song.record_mode = not song.record_mode
        elif cc == trans["loop"]:
            song.loop = not song.loop

    def _handle_mpd_knob(self, cc: int, value: int):
        cc_to_track = {v: (k - 1) for k, v in MidiMap.MPD218_KNOB_CCS.items()}
        if cc not in cc_to_track:
            return
        track_idx = cc_to_track[cc]
        song = self.song()
        if track_idx < len(song.tracks):
            song.tracks[track_idx].mixer_device.volume.value = value / 127.0

    def _handle_apc40_pad(self, note: int, velocity: int):
        """APC40 Mk2 pad pressed: convert note to grid (row, col) and store state."""
        # Note range: 36–99 (8×8 grid)
        if note < MidiMap.APC40_PAD_NOTE_BASE or note >= MidiMap.APC40_PAD_NOTE_BASE + 64:
            return
        pad_idx = note - MidiMap.APC40_PAD_NOTE_BASE
        is_pressed = velocity > 0
        self._apc40_pressed_pads[note] = is_pressed
        # Grid position: row = pad_idx // 8, col = pad_idx % 8
        row, col = divmod(pad_idx, 8)
        self.log_message(f"APC40 pad [{row},{col}] ({note}) — {'pressed' if is_pressed else 'released'}")

    def _handle_apc40_cc(self, cc: int, value: int):
        """APC40 Mk2 faders and knobs."""
        # Faders: CC 48–56 (master + 8 tracks)
        if cc in MidiMap.APC40_FADER_CCS.values():
            fader_idx = list(MidiMap.APC40_FADER_CCS.values()).index(cc)
            if fader_idx == 0:
                # Master volume
                pass  # Not directly mapped yet
            else:
                track_idx = fader_idx - 1
                song = self.song()
                if track_idx < len(song.tracks):
                    song.tracks[track_idx].mixer_device.volume.value = value / 127.0
        # Knobs: CC 16–23
        elif cc in MidiMap.APC40_KNOB_CCS.values():
            knob_idx = list(MidiMap.APC40_KNOB_CCS.values()).index(cc)
            self.log_message(f"APC40 knob {knob_idx + 1} — {value}")

    # ------------------------------------------------------------------ #
    # Command dispatcher                                                   #
    # ------------------------------------------------------------------ #

    def _dispatch(self, msg: dict) -> dict:
        cmd    = msg.get("type", "")
        params = msg.get("params", {})

        handlers = {
            # ── session / transport ──────────────────────────────────────
            "get_session_info":       self._get_session_info,
            "start_playback":         self._start_playback,
            "stop_playback":          self._stop_playback,
            "set_tempo":              self._set_tempo,
            # ── tracks ───────────────────────────────────────────────────
            "get_track_info":         self._get_track_info,
            "create_midi_track":      self._create_midi_track,
            "create_audio_track":     self._create_audio_track,
            "set_track_name":         self._set_track_name,
            "set_track_volume":       self._set_track_volume,
            "set_track_pan":          self._set_track_pan,
            "mute_track":             self._mute_track,
            "solo_track":             self._solo_track,
            # ── clips ─────────────────────────────────────────────────────
            "create_clip":            self._create_clip,
            "add_notes_to_clip":      self._add_notes_to_clip,
            "set_clip_name":          self._set_clip_name,
            "fire_clip":              self._fire_clip,
            "stop_clip":              self._stop_clip,
            # ── devices ───────────────────────────────────────────────────
            "set_device_parameter":   self._set_device_parameter,
            # ── drummer (custom extensions) ───────────────────────────────
            "get_keyboard_notes":     self._get_keyboard_notes,
            "enable_auto_drummer":    self._enable_auto_drummer,
            # ── APC40 Mk2 ────────────────────────────────────────────────
            "get_apc40_pad_state":    self._get_apc40_pad_state,
            "get_apc40_active_pads":  self._get_apc40_active_pads,
        }

        fn = handlers.get(cmd)
        if fn is None:
            raise ValueError(f"unknown command: {cmd!r}")
        return fn(params)

    # ------------------------------------------------------------------ #
    # Session / transport                                                  #
    # ------------------------------------------------------------------ #

    def _get_session_info(self, _) -> dict:
        song = self.song()
        tracks = []
        for i, t in enumerate(song.tracks):
            tracks.append({
                "index":        i,
                "name":         t.name,
                "is_midi":      t.has_midi_input,
                "is_audio":     t.has_audio_input,
                "mute":         t.mute,
                "solo":         t.solo,
                "volume":       t.mixer_device.volume.value,
                "pan":          t.mixer_device.panning.value,
                "num_clips":    sum(1 for s in t.clip_slots if s.has_clip),
                "num_devices":  len(t.devices),
            })
        return {
            "tempo":       song.tempo,
            "is_playing":  song.is_playing,
            "record_mode": song.record_mode,
            "loop":        song.loop,
            "tracks":      tracks,
            "num_scenes":  len(song.scenes),
        }

    def _start_playback(self, _) -> dict:
        self.song().continue_playing()
        return {"playing": True}

    def _stop_playback(self, _) -> dict:
        self.song().stop_playing()
        return {"playing": False}

    def _set_tempo(self, p: dict) -> dict:
        bpm = float(p.get("tempo", p.get("bpm", 120)))
        bpm = max(20.0, min(999.0, bpm))
        self.song().tempo = bpm
        return {"tempo": self.song().tempo}

    # ------------------------------------------------------------------ #
    # Tracks                                                               #
    # ------------------------------------------------------------------ #

    def _get_track_info(self, p: dict) -> dict:
        idx   = int(p["track_index"])
        song  = self.song()
        track = song.tracks[idx]
        clips = []
        for si, slot in enumerate(track.clip_slots):
            if slot.has_clip:
                clips.append({
                    "slot_index": si,
                    "name":       slot.clip.name,
                    "length":     slot.clip.length,
                    "is_playing": slot.clip.is_playing,
                })
        devices = []
        for di, dev in enumerate(track.devices):
            devices.append({
                "index": di,
                "name":  dev.name,
                "params": [
                    {"index": pi, "name": pr.name,
                     "value": pr.value, "min": pr.min, "max": pr.max}
                    for pi, pr in enumerate(dev.parameters)
                ],
            })
        return {
            "index":   idx,
            "name":    track.name,
            "is_midi": track.has_midi_input,
            "mute":    track.mute,
            "solo":    track.solo,
            "volume":  track.mixer_device.volume.value,
            "pan":     track.mixer_device.panning.value,
            "clips":   clips,
            "devices": devices,
        }

    def _create_midi_track(self, p: dict) -> dict:
        idx = int(p.get("index", -1))
        self.song().create_midi_track(idx)
        new_track = self.song().tracks[-1] if idx == -1 else self.song().tracks[idx]
        return {"name": new_track.name, "index": list(self.song().tracks).index(new_track)}

    def _create_audio_track(self, p: dict) -> dict:
        idx = int(p.get("index", -1))
        self.song().create_audio_track(idx)
        new_track = self.song().tracks[-1] if idx == -1 else self.song().tracks[idx]
        return {"name": new_track.name, "index": list(self.song().tracks).index(new_track)}

    def _set_track_name(self, p: dict) -> dict:
        track = self.song().tracks[int(p["track_index"])]
        track.name = str(p["name"])
        return {"name": track.name}

    def _set_track_volume(self, p: dict) -> dict:
        vol = max(0.0, min(1.0, float(p["volume"])))
        self.song().tracks[int(p["track_index"])].mixer_device.volume.value = vol
        return {"volume": vol}

    def _set_track_pan(self, p: dict) -> dict:
        pan = max(-1.0, min(1.0, float(p["pan"])))
        self.song().tracks[int(p["track_index"])].mixer_device.panning.value = pan
        return {"pan": pan}

    def _mute_track(self, p: dict) -> dict:
        self.song().tracks[int(p["track_index"])].mute = bool(p.get("mute", True))
        return {"ok": True}

    def _solo_track(self, p: dict) -> dict:
        self.song().tracks[int(p["track_index"])].solo = bool(p.get("solo", True))
        return {"ok": True}

    # ------------------------------------------------------------------ #
    # Clips                                                                #
    # ------------------------------------------------------------------ #

    def _create_clip(self, p: dict) -> dict:
        track_idx = int(p["track_index"])
        slot_idx  = int(p["clip_index"])  # package uses "clip_index"
        length    = float(p.get("length", 4.0))

        song  = self.song()
        track = song.tracks[track_idx]
        slot  = track.clip_slots[slot_idx]
        if not slot.has_clip:
            slot.create_clip(length)
        clip = slot.clip
        clip.loop_end = length
        clip.looping  = True
        return {"name": clip.name, "length": clip.length}

    def _add_notes_to_clip(self, p: dict) -> dict:
        track_idx = int(p["track_index"])
        slot_idx  = int(p["clip_index"])
        raw_notes = p.get("notes", [])

        song = self.song()
        slot = song.tracks[track_idx].clip_slots[slot_idx]
        if not slot.has_clip:
            raise ValueError(f"No clip in track {track_idx} slot {slot_idx}")

        clip = slot.clip
        # Support both key names for compatibility
        note_tuples = tuple(
            (
                int(n["pitch"]),
                float(n.get("start_time", n.get("time", 0))),
                float(n["duration"]),
                int(n.get("velocity", 100)),
                bool(n.get("mute", n.get("muted", False))),
            )
            for n in raw_notes
        )
        clip.set_notes(note_tuples)
        return {"added": len(note_tuples)}

    def _set_clip_name(self, p: dict) -> dict:
        song = self.song()
        slot = song.tracks[int(p["track_index"])].clip_slots[int(p["clip_index"])]
        if not slot.has_clip:
            raise ValueError("No clip in that slot")
        slot.clip.name = str(p["name"])
        return {"name": slot.clip.name}

    def _fire_clip(self, p: dict) -> dict:
        song = self.song()
        song.tracks[int(p["track_index"])].clip_slots[int(p["clip_index"])].fire()
        return {"ok": True}

    def _stop_clip(self, p: dict) -> dict:
        song = self.song()
        song.tracks[int(p["track_index"])].clip_slots[int(p["clip_index"])].stop()
        return {"ok": True}

    # ------------------------------------------------------------------ #
    # Devices                                                              #
    # ------------------------------------------------------------------ #

    def _set_device_parameter(self, p: dict) -> dict:
        track  = self.song().tracks[int(p["track_index"])]
        device = track.devices[int(p.get("device_index", 0))]
        param  = device.parameters[int(p["param_index"])]
        val    = max(param.min, min(param.max, float(p["value"])))
        param.value = val
        return {"param": param.name, "value": val}

    # ------------------------------------------------------------------ #
    # Drummer extensions                                                   #
    # ------------------------------------------------------------------ #

    def _get_keyboard_notes(self, _) -> dict:
        return {"notes": sorted(self._active_keys)}

    def _enable_auto_drummer(self, p: dict) -> dict:
        self._auto_drummer = bool(p.get("enabled", True))
        return {"auto_drummer": self._auto_drummer}

    # ------------------------------------------------------------------ #
    # APC40 Mk2 support                                                    #
    # ------------------------------------------------------------------ #

    def _get_apc40_pad_state(self, p: dict) -> dict:
        """Query state of a specific APC40 pad by grid coordinates or note."""
        if "note" in p:
            note = int(p["note"])
            return {"note": note, "pressed": self._apc40_pressed_pads.get(note, False)}
        elif "row" in p and "col" in p:
            row, col = int(p["row"]), int(p["col"])
            if 0 <= row < 8 and 0 <= col < 8:
                note = MidiMap.APC40_PAD_NOTE_BASE + (row * 8 + col)
                return {"row": row, "col": col, "note": note, "pressed": self._apc40_pressed_pads.get(note, False)}
        raise ValueError("Provide either 'note' or 'row'+'col'")

    def _get_apc40_active_pads(self, _) -> dict:
        """Return all currently pressed APC40 pads as list of [row, col] coordinates."""
        pressed = []
        for note, is_pressed in self._apc40_pressed_pads.items():
            if is_pressed:
                pad_idx = note - MidiMap.APC40_PAD_NOTE_BASE
                if 0 <= pad_idx < 64:
                    row, col = divmod(pad_idx, 8)
                    pressed.append({"row": row, "col": col, "note": note})
        return {"active_pads": pressed}
