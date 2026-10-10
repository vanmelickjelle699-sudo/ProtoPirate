#!/usr/bin/env python3
"""Base44 preview surface for ProtoPirate.

ProtoPirate is a Flipper Zero *firmware* application (.fap): it is written in C,
has no HTTP server and no browser UI, and runs on Flipper Zero hardware once it
has been compiled with `ufbt`. Nothing about it can be rendered in a browser.

The Base44 preview expects an HTTP surface on port 3000, so this small helper
bridges the gap: it compiles the app with `ufbt` and serves a read-only build
report plus the resulting `dist/proto_pirate.fap` for download.

Sandbox-only helper — not part of the application itself.
"""

from __future__ import annotations

import glob
import html
import http.server
import os
import subprocess
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
LOG_PATH = os.path.join(DIST, "build.log")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "3000"))

_build = {
    "status": "building",  # building | success | failed
    "started": None,
    "finished": None,
    "returncode": None,
}


def run_build() -> None:
    os.makedirs(DIST, exist_ok=True)
    _build["status"] = "building"
    _build["started"] = time.time()
    _build["finished"] = None
    _build["returncode"] = None
    with open(LOG_PATH, "w", encoding="utf-8") as log:
        log.write(f"$ ufbt   (cwd={ROOT})\n\n")
        log.flush()
        try:
            proc = subprocess.run(["ufbt"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            code = proc.returncode
        except FileNotFoundError as exc:
            log.write(f"\nERROR: {exc}\n`ufbt` is not installed in this container.\n")
            code = 127
    _build["returncode"] = code
    _build["status"] = "success" if code == 0 else "failed"
    _build["finished"] = time.time()


def artifact_path():
    faps = sorted(glob.glob(os.path.join(DIST, "*.fap")))
    return faps[0] if faps else None


def _log_tail(lines: int = 60) -> str:
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as fh:
            data = fh.readlines()
    except OSError:
        return "No build log yet."
    return "".join(data[-lines:]).strip() or "No build output yet."


def render_page() -> str:
    status = _build["status"]
    fap = artifact_path()
    if status == "building":
        badge, colour, blurb = "BUILDING", "#e0a800", "Compiling with ufbt — this page refreshes itself."
    elif status == "success":
        badge, colour, blurb = "BUILD SUCCESSFUL", "#2f9e44", "The application compiled and is ready to install."
    else:
        badge, colour, blurb = "BUILD FAILED", "#e03131", "See the log below for the compiler error."

    duration = ""
    if _build["started"] and _build["finished"]:
        duration = f"{_build['finished'] - _build['started']:.1f}s"

    size = ""
    if fap and os.path.exists(fap):
        size = f"{os.path.getsize(fap) / 1024:.1f} KB"

    download = ""
    if fap:
        name = os.path.basename(fap)
        download = (
            f'<p><a class="dl" href="/{html.escape(name)}" download>&#11015; Download '
            f'{html.escape(name)}</a> <span class="muted">({size})</span></p>'
        )

    refresh = '<meta http-equiv="refresh" content="4">' if status == "building" else ""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">{refresh}
<title>ProtoPirate — build report</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin:0; background:#0d1117; color:#e6edf3;
         font:15px/1.5 ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif; }}
  main {{ max-width:820px; margin:0 auto; padding:40px 22px 60px; }}
  h1 {{ font-size:26px; margin:0 0 4px; }}
  .sub {{ color:#8b949e; margin:0 0 24px; }}
  .badge {{ display:inline-block; background:{colour}; color:#fff; font-weight:700;
            letter-spacing:.04em; font-size:12px; padding:5px 11px; border-radius:999px; }}
  .card {{ background:#161b22; border:1px solid #30363d; border-radius:12px;
           padding:20px 22px; margin:18px 0; }}
  .card p {{ margin:8px 0; }}
  .muted {{ color:#8b949e; }}
  table {{ border-collapse:collapse; width:100%; }}
  td {{ padding:5px 0; vertical-align:top; }}
  td:first-child {{ color:#8b949e; width:150px; }}
  a {{ color:#58a6ff; }}
  a.dl {{ display:inline-block; background:#238636; color:#fff; text-decoration:none;
          font-weight:600; padding:9px 16px; border-radius:8px; }}
  pre {{ background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:14px;
         overflow:auto; max-height:340px; font-size:12.5px; line-height:1.45;
         font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
  code {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
</style></head><body><main>
  <h1>ProtoPirate</h1>
  <p class="sub">Flipper Zero Sub-GHz application — build report</p>
  <span class="badge">{badge}</span> <span class="muted">{blurb}</span>

  <div class="card">
    <p><b>This repository is a Flipper Zero firmware app, not a website.</b>
    It is written in C and compiles with <code>ufbt</code> into a single
    <code>.fap</code> file that runs on Flipper Zero hardware — there is no web
    interface to display in a browser. This page reports the build of that app
    and lets you download the result.</p>
  </div>

  <div class="card">
    <table>
      <tr><td>Build status</td><td>{html.escape(status)}</td></tr>
      <tr><td>Build time</td><td>{html.escape(duration) or '&mdash;'}</td></tr>
      <tr><td>Artifact</td><td><code>{html.escape(os.path.basename(fap)) if fap else 'proto_pirate.fap'}</code>{(' &middot; ' + size) if size else ''}</td></tr>
      <tr><td>Target</td><td>Flipper Zero (f7)</td></tr>
    </table>
    {download}
  </div>

  <div class="card">
    <p class="muted">Build log (last lines) &middot; <a href="/build.log">full log</a></p>
    <pre>{html.escape(_log_tail())}</pre>
  </div>

  <p class="muted" style="font-size:13px">To install: copy the <code>.fap</code> to
  <code>/ext/apps/Sub-GHz/</code> on the Flipper's SD card, or connect the device
  over USB and run <code>ufbt launch</code>.</p>
</main></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str, extra=None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, render_page().encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/build.log":
            self._send(200, _log_tail(lines=100000).encode("utf-8"), "text/plain; charset=utf-8")
        elif path.endswith(".fap"):
            fap = artifact_path()
            if fap and os.path.basename(fap) == os.path.basename(path):
                with open(fap, "rb") as fh:
                    body = fh.read()
                self._send(
                    200,
                    body,
                    "application/octet-stream",
                    {"Content-Disposition": f'attachment; filename="{os.path.basename(fap)}"'},
                )
            else:
                self._send(404, b"Not built yet\n", "text/plain; charset=utf-8")
        else:
            self._send(404, b"Not found\n", "text/plain; charset=utf-8")

    def do_HEAD(self):  # noqa: N802
        self.do_GET()

    def log_message(self, *args) -> None:  # keep container logs quiet
        pass


def main() -> None:
    threading.Thread(target=run_build, daemon=True).start()
    with http.server.ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        print(f"ProtoPirate build report on http://{HOST}:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
