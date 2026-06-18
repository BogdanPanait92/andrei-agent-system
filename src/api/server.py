"""Lightweight HTTP server for Railway health checks and job triggers."""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import src.bootstrap  # noqa: F401

from src.jobs.alerts import run_smart_alerts
from src.jobs.daily_briefing import run_daily_briefing
from src.jobs.weekly_review import run_weekly_review
from src.utils.config import settings
from src.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


class Handler(BaseHTTPRequestHandler):
    def _json_response(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._json_response(200, '{"status":"ok","service":"andreia-agents"}')
            return

        if parsed.path == "/":
            self._json_response(200, '{"service":"Andrei AI Agent System","version":"1.0.0"}')
            return

        self._json_response(404, '{"error":"not found"}')

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        routes = {
            "/trigger/daily": run_daily_briefing,
            "/trigger/weekly": run_weekly_review,
            "/trigger/alerts": run_smart_alerts,
        }

        if parsed.path not in routes:
            self._json_response(404, '{"error":"not found"}')
            return

        def _run():
            try:
                result = routes[parsed.path]()
                logger.info("trigger_completed", path=parsed.path)
            except Exception as e:
                logger.error("trigger_failed", path=parsed.path, error=str(e))

        threading.Thread(target=_run, daemon=True).start()
        self._json_response(202, '{"status":"accepted","message":"job started"}')

    def log_message(self, format, *args):
        logger.debug("http_request", message=format % args)


def _start_discord_bot_background() -> None:
    if not settings.enable_discord_bot or not settings.discord_bot_token.strip():
        return

    def _run() -> None:
        try:
            from src.bot.discord_bot import run_discord_bot

            run_discord_bot()
        except Exception as e:
            logger.error("discord_bot_background_failed", error=str(e))

    threading.Thread(target=_run, daemon=True, name="discord-bot").start()
    logger.info("discord_bot_background_started")


def main() -> None:
    _start_discord_bot_background()
    port = int(os.environ.get("PORT", settings.port))
    server = HTTPServer(("0.0.0.0", port), Handler)
    logger.info("api_server_started", port=port)
    server.serve_forever()


if __name__ == "__main__":
    main()