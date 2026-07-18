"""
Frontend development server with reverse proxy to backend API.

Serves static files from this directory on port 5500.
Proxies the following paths to http://localhost:5001:
  /api/*          → http://localhost:5001/<rest>  (strips /api prefix)
  /auth/*         → http://localhost:5001/auth/*
  /pdf/*          → http://localhost:5001/pdf/*
  /ocr/*          → http://localhost:5001/ocr/*
  /ai/*           → http://localhost:5001/ai/*
  /files/*        → http://localhost:5001/files/*
  /feedback/*     → http://localhost:5001/feedback/*
  /convert/*      → http://localhost:5001/convert/*
  /edit/*         → http://localhost:5001/edit/*
  /security/*     → http://localhost:5001/security/*
  /image/*        → http://localhost:5001/image/*
  /utils/*        → http://localhost:5001/utils/*
  /productivity/* → http://localhost:5001/productivity/*
  /health         → http://localhost:5001/health
"""

import http.server
import socketserver
import socket
import mimetypes
import os
import urllib.request
import urllib.error

# Disable system proxies for all urllib.request calls to avoid routing localhost through them
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
urllib.request.install_opener(opener)
mimetypes.init()
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/svg+xml', '.svg')

PORT = 5500
BACKEND = 'http://127.0.0.1:5001'
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Paths that should be proxied to the backend
PROXY_PREFIXES = (
    '/api/',
    '/auth/', '/auth',
    '/pdf/', '/pdf',
    '/ocr/', '/ocr',
    '/ai/', '/ai',
    '/files/', '/files',
    '/feedback/', '/feedback',
    '/convert/', '/convert',
    '/edit/', '/edit',
    '/security/', '/security',
    '/image/', '/image',
    '/utils/', '/utils',
    '/productivity/', '/productivity',
    '/health',
)


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def _should_proxy(self):
        path = self.path.split('?')[0]
        return any(path == p or path.startswith(p) for p in PROXY_PREFIXES)

    def _proxy_request(self):
        # Strip /api prefix if present, then forward to backend
        target_path = self.path
        if target_path.startswith('/api/'):
            target_path = target_path[4:]  # strip /api → /convert/... etc.
        elif target_path == '/api':
            target_path = '/'

        target_url = BACKEND + target_path

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build proxied request headers
        proxy_headers = {}
        hop_by_hop = {'connection', 'keep-alive', 'proxy-authenticate',
                      'proxy-authorization', 'te', 'trailers',
                      'transfer-encoding', 'upgrade', 'host'}
        for key, val in self.headers.items():
            if key.lower() not in hop_by_hop:
                proxy_headers[key] = val

        try:
            req = urllib.request.Request(
                target_url,
                data=body,
                headers=proxy_headers,
                method=self.command
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                self.send_response(resp.status)
                # Forward response headers
                for key, val in resp.headers.items():
                    if key.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(key, val)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for key, val in e.headers.items():
                if key.lower() not in ('transfer-encoding', 'connection'):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            msg = f'{{"error": "Proxy error: {str(e)}"}}'.encode()
            self.wfile.write(msg)

    def do_GET(self):
        if self._should_proxy():
            self._proxy_request()
        else:
            super().do_GET()

    def do_POST(self):
        if self._should_proxy():
            self._proxy_request()
        else:
            self.send_response(405)
            self.end_headers()

    def do_PUT(self):
        if self._should_proxy():
            self._proxy_request()
        else:
            self.send_response(405)
            self.end_headers()

    def do_DELETE(self):
        if self._should_proxy():
            self._proxy_request()
        else:
            self.send_response(405)
            self.end_headers()

    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, X-Gemini-Key')
        self.end_headers()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        # Suppress noisy static file logs, show proxy ones
        if self._should_proxy():
            print(f'[Proxy] {self.command} {self.path} -> {args[1]}')


class DualStackTCPServer(socketserver.TCPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


if __name__ == '__main__':
    # Use IPv4 loopback to avoid DualStackTCPServer crashes on Windows
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), ProxyHandler) as httpd:
        print("==================================================")
        print("  AI DocMaster Frontend Server + API Proxy Active")
        print(f"  Static files: http://localhost:{PORT}")
        print(f"  API proxy: /api/* -> {BACKEND}")
        print(f"  Direct proxy: /edit /auth /pdf /ocr /ai etc -> {BACKEND}")
        print("==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down frontend server.")
