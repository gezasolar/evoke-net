from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from .client import APIError, Client
from .comfyui import ComfyUIError, render as render_comfyui

DEFAULT_URL = "https://evoke.tbbw.net"
CONFIG_PATH = Path.home() / ".config" / "evokenet" / "node.json"


def _gpu() -> tuple[str, float]:
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True, timeout=5)
        name, vram = out.splitlines()[0].split(",", 1)
        return name.strip(), float(vram.strip()) / 1024
    except Exception:
        return "Unknown GPU", 0.0


def load() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except FileNotFoundError:
        raise SystemExit("No node is activated. Run: evokenet activate EVK-XXXXXX")


def save(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(CONFIG_PATH)


def cmd_activate(args: argparse.Namespace) -> int:
    name, vram = _gpu()
    client = Client(args.url)
    registered = client.register(args.join_code, args.name or platform.node(), platform.system(), name, vram)
    save({"base_url": args.url, "node_token": registered["node_token"], "node_id": registered["node_id"],
          "gpu_name": name, "vram_gb": vram, "renderer": "", "enabled": False})
    print("Node activated as %s (%s). It is paused by default." % (registered["node_id"], registered["hw_tier"]))
    print("Configure an explicit local renderer, then run: evokenet run --enable")
    return 0


def configured_client(config: dict) -> Client:
    return Client(config["base_url"], config["node_token"])


def cmd_status(args: argparse.Namespace) -> int:
    config = load(); result = configured_client(config).me()
    print(json.dumps({"local_enabled": config.get("enabled", False), "renderer_configured": bool(config.get("renderer")), "remote": result}, indent=2))
    return 0


def cmd_renderer(args: argparse.Namespace) -> int:
    config = load(); config["renderer"] = args.command; save(config)
    print("Renderer stored. Evoke will pass only JSON on stdin and requires result.png in the supplied output path.")
    return 0


def cmd_comfyui(args: argparse.Namespace) -> int:
    config = load()
    config["renderer"] = ""
    config["comfyui"] = {"url": args.url.rstrip("/"), "checkpoint": args.checkpoint}
    save(config)
    print("ComfyUI renderer stored. It will use only your local server and checkpoint.")
    return 0


def render(config: dict, job: dict) -> Path:
    command = config.get("renderer")
    comfy = config.get("comfyui") or {}
    if not command and not comfy:
        raise RuntimeError("No renderer configured. Use: evokenet renderer '<your-local-command>'")
    with tempfile.TemporaryDirectory(prefix="evokenet-") as directory:
        root = Path(directory); job_path = root / "job.json"; output = root / "result.png"
        job_path.write_text(json.dumps(job["payload"]))
        env = {"PATH": os.environ.get("PATH", ""), "EVOKE_JOB_JSON": str(job_path), "EVOKE_OUTPUT_PATH": str(output)}
        started = time.monotonic()
        if comfy:
            render_comfyui(job["payload"], output, comfy["url"], comfy["checkpoint"], max(60, int(job.get("deadline_s", 300))))
        else:
            # Command originates from the node owner's local configuration, never from the server.
            subprocess.run(command, shell=True, check=True, stdin=job_path.open("rb"), env=env, timeout=max(30, int(job.get("deadline_s", 300))))
        if not output.is_file():
            raise RuntimeError("renderer finished without writing EVOKE_OUTPUT_PATH")
        fd, result_path = tempfile.mkstemp(prefix="evokenet-result-", suffix=".png")
        os.close(fd)
        persistent = Path(result_path)
        persistent.write_bytes(output.read_bytes())
        return persistent


def cmd_run(args: argparse.Namespace) -> int:
    config = load()
    if not args.enable:
        raise SystemExit("Safety gate: add --enable for an attended pilot run. The node is paused by default.")
    if not config.get("renderer") and not config.get("comfyui"):
        raise SystemExit("No renderer configured. Run evokenet renderer or evokenet comfyui first.")
    config["enabled"] = True; save(config); client = configured_client(config)
    print("Running one attended job. Ctrl-C stops before the next claim.")
    client.heartbeat("online")
    job = client.claim()
    if not job:
        print("No job available."); return 0
    try:
        started = time.monotonic(); output = render(config, job)
        result = client.submit_result(job["job_id"], output, time.monotonic() - started, datetime.now().hour)
        output.unlink(missing_ok=True); print(json.dumps(result, indent=2)); return 0
    except Exception:
        client.heartbeat("paused")
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evokenet", description="Evoke Net pilot node")
    parser.add_argument("--url", default=DEFAULT_URL)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("activate"); a.add_argument("join_code"); a.add_argument("--name"); a.set_defaults(func=cmd_activate)
    s = sub.add_parser("status"); s.set_defaults(func=cmd_status)
    r = sub.add_parser("renderer"); r.add_argument("command"); r.set_defaults(func=cmd_renderer)
    c = sub.add_parser("comfyui", help="configure a locally running ComfyUI instance")
    c.add_argument("--url", default="http://127.0.0.1:8188")
    c.add_argument("--checkpoint", required=True, help="checkpoint filename already installed in your ComfyUI models/checkpoints folder")
    c.set_defaults(func=cmd_comfyui)
    run = sub.add_parser("run"); run.add_argument("--enable", action="store_true"); run.set_defaults(func=cmd_run)
    args = parser.parse_args(argv)
    try: return args.func(args)
    except APIError as exc: print("Evoke API error:", exc, file=sys.stderr); return 2
    except Exception as exc: print("Evoke node error:", exc, file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
