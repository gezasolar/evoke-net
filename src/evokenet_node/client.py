"""Small, stdlib-only client for Evoke Net's node API.

The client never evaluates server-provided code. A node owner explicitly
configures their local renderer; job JSON is supplied only through stdin.
"""
from __future__ import annotations

import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


class APIError(RuntimeError):
    pass


class Client:
    def __init__(self, base_url: str, node_token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.node_token = node_token

    def _request(self, method: str, path: str, body: bytes | None = None,
                 content_type: str = "application/json") -> dict | None:
        headers = {"Accept": "application/json"}
        if self.node_token:
            headers["X-Node-Token"] = self.node_token
        if body is not None:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(self.base_url + path, data=body,
                                         headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise APIError("%s %s: %s" % (exc.code, path, detail)) from exc
        except urllib.error.URLError as exc:
            raise APIError("network error: %s" % exc.reason) from exc

    def post_json(self, path: str, data: dict) -> dict | None:
        return self._request("POST", path, json.dumps(data).encode(), "application/json")

    def register(self, join_code: str, name: str, os_name: str, gpu_name: str,
                 vram_gb: float) -> dict:
        # Registration has no credential until the server returns one.
        return self.post_json("/node/register", {"join_code": join_code, "name": name,
            "os": os_name, "gpu_name": gpu_name, "vram_gb": vram_gb}) or {}

    def heartbeat(self, status: str) -> dict:
        return self.post_json("/node/heartbeat", {"status": status}) or {}

    def claim(self) -> dict | None:
        return self.post_json("/node/claim?wait=25", {})

    def me(self) -> dict:
        return self._request("GET", "/node/me") or {}

    def submit_result(self, job_id: str, image_path: Path, exec_seconds: float,
                      local_hour: int) -> dict:
        data = image_path.read_bytes()
        import hashlib
        fields = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "exec_seconds": str(round(exec_seconds, 3)),
            "local_hour": str(local_hour),
        }
        boundary = "----evokenet" + uuid.uuid4().hex
        parts: list[bytes] = []
        for key, value in fields.items():
            parts.extend([("--%s\r\n" % boundary).encode(),
                ('Content-Disposition: form-data; name="%s"\r\n\r\n' % key).encode(),
                value.encode(), b"\r\n"])
        parts.extend([("--%s\r\n" % boundary).encode(),
            b'Content-Disposition: form-data; name="image"; filename="result.png"\r\n',
            ("Content-Type: %s\r\n\r\n" % (mimetypes.guess_type(str(image_path))[0] or "image/png")).encode(),
            data, b"\r\n", ("--%s--\r\n" % boundary).encode()])
        return self._request("POST", "/node/result/%s" % urllib.parse.quote(job_id),
                             b"".join(parts), "multipart/form-data; boundary=" + boundary) or {}
