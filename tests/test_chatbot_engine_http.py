from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from chatbot.engine.llm_engine import LLMEngine

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "chatbot" / "knowledge"


def test_llm_engine_http_round_trip_with_local_openai_compatible_stub():
    requests: list[dict] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            requests.append(payload)
            body = json.dumps(
                {"choices": [{"message": {"content": "stubbed local response"}}]}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        engine = LLMEngine(
            _KNOWLEDGE_DIR,
            vllm_url=f"http://127.0.0.1:{server.server_port}",
            timeout_s=2.0,
        )
        result = engine.query("보세전시장이 무엇인가요?")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert result is not None
    assert result.source == "llm"
    assert result.answer == "stubbed local response"
    assert requests
    assert requests[0]["model"] == engine.model
    assert requests[0]["messages"][0]["role"] == "system"
