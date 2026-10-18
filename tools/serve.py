#!/usr/bin/env python3
"""Simple static server for the mushaf site with HTTP Range support (needed by PDF.js).

    python tools/serve.py            -> http://localhost:8000
    python tools/serve.py 9000
"""
import os, re, sys, http.server, socketserver, functools

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".mjs": "text/javascript",
        ".js": "text/javascript",
        ".json": "application/json",
        ".webmanifest": "application/manifest+json",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
        ".woff2": "font/woff2",
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        fs = os.fstat(f.fileno())
        size = fs[6]
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        if not m:
            f.close()
            return super().send_head()
        start_s, end_s = m.groups()
        if start_s:
            start = int(start_s); end = int(end_s) if end_s else size - 1
        else:
            length = int(end_s); start = size - length; end = size - 1
        if start >= size or start > end:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        end = min(end, size - 1)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        f.seek(start)
        return _Limited(f, end - start + 1)

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

class _Limited:
    def __init__(self, f, n):
        self.f = f; self.n = n
    def read(self, k=-1):
        if self.n <= 0: return b""
        if k is None or k < 0 or k > self.n: k = self.n
        d = self.f.read(k); self.n -= len(d); return d
    def close(self): self.f.close()

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print(f"مصحف طلعت فتحي محمد — الخادم يعمل على  http://localhost:{PORT}")
        print("اضغط Ctrl+C للإيقاف")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nتم الإيقاف")