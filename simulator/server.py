"""
Simplex Computer Web Server & Runner
Serves the simulator Web UI and provides a local HTTP interface.
"""

import http.server
import socketserver
import os
import sys
import webbrowser
import argparse

DEFAULT_PORT = 8080


class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
        super().__init__(*args, directory=web_dir, **kwargs)

    def log_message(self, format, *args):
        # Clean logging
        sys.stdout.write(f"[Simplex Server] {args[0]} - {args[1]}\n")
        sys.stdout.flush()


def run_server(port: int = DEFAULT_PORT, open_browser: bool = True):
    web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
    if not os.path.exists(web_dir):
        print(f"Error: Web directory not found at {web_dir}")
        sys.exit(1)

    url = f"http://localhost:{port}"
    print("=" * 60)
    print("  SIMPLEX COMPUTER 16-BIT SIMULATOR")
    print("  GIKI CS222 Architecture Project")
    print("=" * 60)
    print(f"  Serving Web UI from: {web_dir}")
    print(f"  Local URL:           {url}")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 60)

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    with socketserver.TCPServer(("", port), QuietHTTPHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Simplex Computer Web Simulator")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to serve on (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    args = parser.parse_args()

    run_server(port=args.port, open_browser=not args.no_browser)
