from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..config.schema import SystemConfig
from .render import render_monitoring_dashboard
from .service import MonitoringSnapshotService


def serve_monitoring_dashboard(
    config: SystemConfig,
    *,
    host: str,
    port: int,
    title: str,
    decision_limit: int,
    execution_limit: int,
    stale_after_seconds: int,
    refresh_seconds: int,
) -> None:
    project_root = Path(__file__).resolve().parents[3]
    snapshot_service = MonitoringSnapshotService(
        config.database.url,
        project_root=project_root,
    )

    class MonitoringHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            snapshot = snapshot_service.build_snapshot(
                decision_limit=decision_limit,
                execution_limit=execution_limit,
                stale_after_seconds=stale_after_seconds,
            )
            if path in {"/", "/index.html"}:
                html = render_monitoring_dashboard(
                    snapshot,
                    title=title,
                    refresh_seconds=refresh_seconds,
                ).encode("utf-8")
                self._send_bytes(
                    HTTPStatus.OK,
                    html,
                    content_type="text/html; charset=utf-8",
                )
                return

            if path == "/api/snapshot":
                payload = json.dumps(snapshot, indent=2, ensure_ascii=False).encode("utf-8")
                self._send_bytes(
                    HTTPStatus.OK,
                    payload,
                    content_type="application/json; charset=utf-8",
                )
                return

            if path == "/health":
                body = {
                    "status": snapshot["runtime"]["status"],
                    "database_exists": snapshot["database"]["exists"],
                }
                status_code = (
                    HTTPStatus.OK
                    if snapshot["runtime"]["status"] in {"healthy", "stale", "inactive"}
                    else HTTPStatus.SERVICE_UNAVAILABLE
                )
                self._send_bytes(
                    status_code,
                    json.dumps(body, ensure_ascii=False).encode("utf-8"),
                    content_type="application/json; charset=utf-8",
                )
                return

            self._send_bytes(
                HTTPStatus.NOT_FOUND,
                b'{"error":"not_found"}',
                content_type="application/json; charset=utf-8",
            )

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _send_bytes(
            self,
            status_code: HTTPStatus,
            payload: bytes,
            *,
            content_type: str,
        ) -> None:
            self.send_response(int(status_code))
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer((host, port), MonitoringHandler)
    try:
        print(
            json.dumps(
                {
                    "serving": True,
                    "host": host,
                    "port": port,
                    "title": title,
                    "database_url": config.database.url,
                    "refresh_seconds": refresh_seconds,
                    "decision_limit": decision_limit,
                    "execution_limit": execution_limit,
                    "stale_after_seconds": stale_after_seconds,
                    "dashboard_url": f"http://{host}:{port}/",
                    "snapshot_url": f"http://{host}:{port}/api/snapshot",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
