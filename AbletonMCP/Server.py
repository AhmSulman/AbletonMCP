"""
TCP socket server running inside Ableton.
Protocol: JSON over TCP on localhost:9877 (one object per message, no delimiter)
  receive:  {"type": "<cmd>", "params": {...}}
  send:     {"status": "ok",    "result": {...}}
          | {"status": "error", "message": "..."}
"""

import json
import queue
import socket
import threading
import uuid

HOST = "127.0.0.1"
PORT = 9877


def _client_loop(conn: socket.socket, command_queue: queue.Queue):
    buf = b""
    try:
        conn.settimeout(None)
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            # Try to parse as complete JSON (the upstream client sends one JSON
            # object at a time without a delimiter, so we try after every chunk)
            try:
                msg = json.loads(buf.decode("utf-8"))
                buf = b""
            except json.JSONDecodeError:
                continue  # keep buffering

            response_q: queue.Queue = queue.Queue()
            command_queue.put((str(uuid.uuid4()), msg, response_q))
            try:
                result = response_q.get(timeout=15)
            except queue.Empty:
                result = {"status": "error", "message": "Ableton response timeout"}

            conn.sendall(json.dumps(result).encode("utf-8"))
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def start_server_thread(command_queue: queue.Queue) -> socket.socket:
    """Bind a TCP server socket and accept connections in background threads."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)

    def _accept_loop():
        while True:
            try:
                conn, _ = server_sock.accept()
                t = threading.Thread(
                    target=_client_loop, args=(conn, command_queue), daemon=True
                )
                t.start()
            except Exception:
                break  # server_sock was closed (disconnect)

    t = threading.Thread(target=_accept_loop, daemon=True)
    t.start()
    return server_sock
