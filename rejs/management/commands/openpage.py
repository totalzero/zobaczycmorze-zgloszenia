"""Management command to open pages in browser with optional server start."""

import os
import socket
import threading
import time
import webbrowser

from django.core.management import call_command
from django.core.management.base import BaseCommand


def is_server_running(host="127.0.0.1", port=8000):
	"""Check if Django dev server is running."""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		return s.connect_ex((host, port)) == 0


class Command(BaseCommand):
	"""Open page in browser, starting server if needed."""

	help = "Open page in browser, starting server if needed"

	def add_arguments(self, parser):
		parser.add_argument(
			"--admin",
			action="store_true",
			help="Open admin page instead of main page",
		)
		parser.add_argument(
			"--port",
			type=int,
			default=8000,
			help="Port number (default: 8000)",
		)

	def handle(self, *args, **options):
		port = options["port"]
		path = "/admin/" if options["admin"] else "/"
		url = f"http://127.0.0.1:{port}{path}"

		# Skip browser open in reloader child process (RUN_MAIN is set by Django reloader)
		is_reloader_child = os.environ.get("RUN_MAIN") == "true"

		if is_server_running(port=port):
			if not is_reloader_child:
				self.stdout.write(f"Server already running. Opening {url}")
				webbrowser.open(url)
		else:
			if not is_reloader_child:
				self.stdout.write(f"Starting server and opening {url}")

				# Open browser after short delay
				def open_browser():
					time.sleep(2)
					webbrowser.open(url)

				threading.Thread(target=open_browser, daemon=True).start()

			# Start server (blocks)
			call_command("runserver", f"127.0.0.1:{port}")
