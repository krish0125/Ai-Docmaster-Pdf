import socket
import socketserver
import http.server
import requests

PORT = 5502

class DualStackTCPServer(socketserver.TCPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello from Dual Stack Server!")

# Run server in background and try contacting it via IPv4 and IPv6
import threading
server = DualStackTCPServer(("::", PORT), SimpleHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

print("Server started. Testing requests...")
try:
    r_ip = requests.get(f"http://127.0.0.1:{PORT}/", timeout=2)
    print("127.0.0.1 connection:", r_ip.status_code, r_ip.text)
except Exception as e:
    print("127.0.0.1 failed:", e)

try:
    r_lh = requests.get(f"http://localhost:{PORT}/", timeout=2)
    print("localhost connection:", r_lh.status_code, r_lh.text)
except Exception as e:
    print("localhost failed:", e)

server.shutdown()
server.server_close()
print("Server closed.")
