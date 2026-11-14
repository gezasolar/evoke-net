"""Explicit local ComfyUI adapter for the Evoke Net pilot.

This module only talks to an operator-selected ComfyUI URL (normally their
own ``http://127.0.0.1:8188``).  It never executes anything received from the
Evoke server; it converts the image parameters into a fixed local workflow.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


class ComfyUIError(RuntimeError):
    pass


def _request(url: str, method: str = "GET", data: dict | None = None) -> dict:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def _workflow(payload: dict, checkpoint: str) -> dict:
    width = int(payload.get("width", 512))
    height = int(payload.get("height", 512))
    steps = int(payload.get("steps", 25))
    seed = int(payload.get("seed") or int(time.time() * 1000) % (2**63 - 1))
    prompt = str(payload.get("prompt") or "")
    guidance = float(payload.get("guidance", 7.5))
    # Standard ComfyUI built-in nodes.  The checkpoint remains entirely local.
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": guidance,
              "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
              "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "evokenet", "images": ["6", 0]}},
    }


def render(payload: dict, output_path: Path, base_url: str, checkpoint: str,
           timeout_seconds: int = 600) -> None:
    """Run one fixed workflow on the selected local ComfyUI server."""
    base = base_url.rstrip("/")
    client_id = "evokenet-" + uuid.uuid4().hex
    try:
        queued = _request(base + "/prompt", "POST", {"prompt": _workflow(payload, checkpoint), "client_id": client_id})
    except Exception as exc:
        raise ComfyUIError("cannot reach local ComfyUI at %s: %s" % (base, exc)) from exc
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise ComfyUIError("ComfyUI rejected the local workflow: %s" % queued)
    deadline = time.monotonic() + timeout_seconds
    record = None
    while time.monotonic() < deadline:
        history = _request(base + "/history/" + urllib.parse.quote(str(prompt_id)))
        record = history.get(prompt_id)
        if record:
            break
        time.sleep(1)
    if not record:
        raise ComfyUIError("ComfyUI did not finish before the timeout")
    if record.get("status", {}).get("status_str") == "error":
        raise ComfyUIError("ComfyUI workflow failed: %s" % record.get("status"))
    images = record.get("outputs", {}).get("7", {}).get("images", [])
    if not images:
        raise ComfyUIError("ComfyUI completed without an output image")
    image = images[0]
    query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")})
    try:
        with urllib.request.urlopen(base + "/view?" + query, timeout=60) as response:
            output_path.write_bytes(response.read())
    except Exception as exc:
        raise ComfyUIError("could not fetch the local ComfyUI image: %s" % exc) from exc
