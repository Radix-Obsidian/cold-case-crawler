#!/usr/bin/env python3
"""Simple HTTP server to serve the frontend."""

import http.server
import socketserver
import os
import webbrowser

PORT = 3000
DIRECTORY = "frontend"

os.chdir(DIRECTORY)

Handler = http.server.SimpleHTTPRequestHandler

print(f"🔍 Cold Case Crawler")
print(f"=" * 40)
print(f"🌐 Server running at http://localhost:{PORT}")
print(f"📁 Serving files from: {DIRECTORY}/")
print(f"⌨️  Press Ctrl+C to stop")
print(f"=" * 40)

# Open browser
webbrowser.open(f"http://localhost:{PORT}")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")