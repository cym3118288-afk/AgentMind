"""AgentMind Frontend Server - SpaceX Mission Control UI.

Serves the frontend SPA and displays startup information.
Run: python frontend/server.py
"""

import http.server
import socketserver
import os
import sys
import webbrowser
from functools import partial

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

BANNER = """
\033[36m
    ___                    __  __  _           __
   /   | ____ ____  ____  / /_/  |/ (_)___  __/ /
  / /| |/ __ `/ _ \\/ __ \\/ __/ /|_/ / / __ \\/ __  /
 / ___ / /_/ /  __/ / / / /_/ /  / / / / / / /_/ /
/_/  |_\\__, /\\___/_/ /_/\\__/_/  /_/_/_/ /_/\\__,_/
      /____/
\033[0m
\033[1;37m  MISSION CONTROL INTERFACE\033[0m
\033[90m  ─────────────────────────────────────────\033[0m

\033[32m  [ONLINE]\033[0m  Frontend server running
\033[36m  [PORT]\033[0m    http://localhost:{port}
\033[33m  [NOTE]\033[0m    Start the API backend separately:
\033[90m             uvicorn api_server_enhanced:app --reload\033[0m

\033[90m  Press Ctrl+C to stop the server\033[0m
\033[90m  ─────────────────────────────────────────\033[0m
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        sys.stdout.write(
            f"\033[90m  [{self.log_date_time_string()}]\033[0m "
            f"{format % args}\n"
        )

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def main():
    print(BANNER.format(port=PORT))
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            webbrowser.open(f"http://localhost:{PORT}")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\033[33m  [SHUTDOWN]\033[0m Server stopped.\n")
            httpd.shutdown()


if __name__ == "__main__":
    main()
