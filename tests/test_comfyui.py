import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from evokenet_node.comfyui import render


PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 24000)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200); self.end_headers()
        self.wfile.write(b'{"prompt_id":"p1"}')
    def do_GET(self):
        if self.path.startswith("/history/p1"):
            data = {"p1": {"status": {"status_str": "success"}, "outputs": {"7": {"images": [{"filename":"out.png", "subfolder":"", "type":"output"}]}}}}
            raw = json.dumps(data).encode()
        else:
            raw = PNG
        self.send_response(200); self.end_headers(); self.wfile.write(raw)


class ComfyUITest(unittest.TestCase):
    def test_renders_fixed_workflow_to_output(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as root:
                target = Path(root) / "result.png"
                render({"prompt": "test", "width": 512, "height": 512, "steps": 2}, target,
                       "http://127.0.0.1:%s" % server.server_port, "test.safetensors", 5)
                self.assertEqual(target.read_bytes(), PNG)
        finally:
            server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
