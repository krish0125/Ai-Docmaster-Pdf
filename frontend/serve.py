import http.server
import socketserver
import mimetypes
import os

# Fix MIME types for Windows registry issues
mimetypes.init()
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/svg+xml', '.svg')

PORT = 5500
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Disable caching completely to ensure immediate rendering of style/animation updates
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

if __name__ == '__main__':
    # Force socket reuse to avoid "address already in use" errors on restart
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"==================================================")
        print(f"  AI DocMaster Frontend Server Active")
        print(f"  Serving directory: {DIRECTORY}")
        print(f"  URL: http://localhost:{PORT}")
        print(f"  MIME-types fixed & Caching disabled for development")
        print(f"==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down frontend server.")
