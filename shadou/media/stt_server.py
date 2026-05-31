"""Long-lived STT HTTP sidecar — loads Whisper once, serves transcribe requests."""

from __future__ import annotations

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn

log = logging.getLogger("shadou.stt_server")


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _transcribe(path: str) -> dict:
    from shadou.media.stt_local import transcribe_local

    result = transcribe_local(Path(path))
    return {
        "transcript": result.transcript,
        "confidence": result.confidence,
        "language": result.language,
    }


def _make_handler():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            log.debug(fmt, *args)

        def do_GET(self) -> None:
            if self.path != "/health":
                self.send_error(404)
                return
            body = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path != "/transcribe":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "invalid_json")
                return
            path = str(payload.get("path") or "").strip()
            if not path or not Path(path).is_file():
                self.send_error(400, "missing_path")
                return
            try:
                result = _transcribe(path)
            except Exception as exc:
                log.exception("transcribe failed")
                body = json.dumps({"ok": False, "error": str(exc)[:300]}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            body = json.dumps({"ok": True, **result}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadou local STT sidecar (faster-whisper)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18792)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log.info("loading whisper model (first request may be slow until warm)...")
    from shadou.media.stt_local import _load_model

    _load_model()
    log.info("whisper model ready on %s:%s", args.host, args.port)

    server = _ThreadingHTTPServer((args.host, args.port), _make_handler())
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
