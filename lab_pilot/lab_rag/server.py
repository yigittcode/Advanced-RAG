"""Loopback-only teaching UI. Not an internet-facing production server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from .evaluation import evaluate
from .pipeline import ask
from .providers import ProviderError


def make_server(retriever, query_path, port=8765, client=None, hyde=False, decompose=False):
    lock = threading.Lock()
    web = Path(__file__).parent / "web"
    methods = ["bm25", "lexical"] + (["dense", "hybrid"] if retriever.dense else [])

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, fmt, *args):
            pass  # No questions, contexts, or credentials logged.

        def send(self, data, status=200, kind="application/json; charset=utf-8"):
            body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode() if isinstance(data, dict) else data
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def local_request(self):
            expected = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in expected or (origin and origin != f"http://{host}"):
                self.send({"error": "Yalnızca aynı kaynaktan yerel istek kabul edilir."}, 403)
                return False
            return True

        def do_GET(self):
            if not self.local_request():
                return
            route = urlsplit(self.path).path
            if route == "/api/status":
                self.send({"mode": "llm" if client else "evidence", "llm_model": client.model if client else None,
                           "methods": methods, "documents": len(retriever.corpus.files), "chunks": len(retriever.corpus.chunks),
                           "corpus_sha256": retriever.corpus.fingerprint, "hyde": hyde, "decompose": decompose,
                           "reranker": bool(retriever.reranker)})
            elif route in ("/", "/app.js", "/style.css"):
                file, kind = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}[route]
                self.send((web/file).read_bytes(), kind=kind+"; charset=utf-8")
            else:
                self.send({"error": "Bulunamadı."}, 404)

        def do_POST(self):
            if not self.local_request():
                return
            try:
                if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                    self.send({"error": "application/json gerekli."}, 415)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    self.send({"error": "İstek boyutu 1..8192 byte olmalı."}, 413)
                    return
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("JSON nesnesi gerekli.")
                method = body.get("method", "bm25")
                k = body.get("k", 5)
                if method not in methods or type(k) is not int or not 1 <= k <= 10:
                    raise ValueError("Yöntem veya k geçersiz.")
                # Single-device teaching workload: do not run concurrent model calls.
                if not lock.acquire(blocking=False):
                    self.send({"error": "Başka bir deney çalışıyor; bitmesini bekleyin."}, 409)
                    return
                try:
                    if self.path == "/api/search":
                        result = ask(retriever, body.get("question"), method, k, 20, client, hyde, decompose)
                    elif self.path == "/api/evaluate":
                        split = body.get("split", "test")
                        if split not in ("dev", "test"):
                            raise ValueError("Split dev veya test olmalı.")
                        result = evaluate(retriever, query_path, [method], split, k, 20, client, hyde, decompose)
                    else:
                        self.send({"error": "Bulunamadı."}, 404)
                        return
                    self.send(result)
                finally:
                    lock.release()
            except (ValueError, TypeError, KeyError) as exc:
                self.send({"error": str(exc)}, 400)
            except ProviderError as exc:
                self.send({"error": str(exc)}, 502)
            except Exception:
                self.send({"error": "Deney tamamlanamadı; CLI ile model/veri yapılandırmasını kontrol edin."}, 500)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server
