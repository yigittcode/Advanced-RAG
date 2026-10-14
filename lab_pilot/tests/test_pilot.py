"""Contract and failure tests; no network beyond local fixture servers."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from lab_rag.core import BM25, Retriever, load_corpus, rrf
from lab_rag.evaluation import evaluate, load_queries, metrics
from lab_rag.pipeline import ask, plan_queries
from lab_rag.providers import ChatClient, ProviderError
from lab_rag.server import make_server

BASE = Path(__file__).resolve().parents[1]


@contextmanager
def serving(server):
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


@contextmanager
def model_server(response, status=200, delay=0):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append({"path": self.path, "body": json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
            time.sleep(delay)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                self.wfile.write(json.dumps(response).encode())
            except (BrokenPipeError, ConnectionResetError):
                pass
        def log_message(self, *args):
            pass
    with serving(ThreadingHTTPServer(("127.0.0.1", 0), Handler)) as url:
        yield url+"/v1", requests


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.corpus = load_corpus(BASE/"data/documents")
        self.retriever = Retriever(self.corpus)

    def test_corpus_and_labels_are_valid(self):
        self.assertEqual(8, len(self.corpus.files))
        self.assertEqual(24, len(self.corpus.chunks))
        self.assertEqual(16, len(load_queries(BASE/"data/queries.jsonl", self.corpus, "test")))

    def test_stable_identity_and_invalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root/"a.md"
            a.write_text("## first | One\n"+"same start "*60+"first ending\n## second | Two\n"+"same start "*60+"second ending", encoding="utf-8")
            first = load_corpus(root, 50, 10)
            again = load_corpus(root, 50, 10)
            self.assertEqual(first, again)
            self.assertEqual(len(first.chunks), len({c.chunk_id for c in first.chunks}))
            self.assertTrue(all(len(c.text.split()) <= 50 for c in first.chunks))
            self.assertTrue(all(c.start_line <= c.end_line for c in first.chunks))
            a.write_text(a.read_text()+" changed", encoding="utf-8")
            changed = load_corpus(root, 50, 10)
            self.assertNotEqual(first.fingerprint, changed.fingerprint)
            self.assertEqual(first.chunks[0].chunk_id, changed.chunks[0].chunk_id)
            self.assertNotEqual(first.chunks[-1].chunk_id, changed.chunks[-1].chunk_id)

    def test_invalid_chunk_config_and_duplicate_sections(self):
        with self.assertRaises(ValueError):
            load_corpus(BASE/"data/documents", 20, 20)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.md").write_text("## same\na\n## same\nb", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_corpus(Path(tmp))

    def test_rank_and_empty_query(self):
        rank = BM25(["gpu rezervasyon", "arşiv dosya"]).search("rezervasyon", 5)
        self.assertEqual(0, rank[0][0])
        self.assertEqual([], BM25(["arşiv dosya"]).search("kuantum", 5))
        with self.assertRaises(ValueError):
            ask(self.retriever, " ")
        with self.assertRaises(ValueError):
            self.retriever.search(["test"], "dense")

    def test_rrf_ignores_score_scale(self):
        self.assertEqual(rrf([[(0, 999), (1, 10)], [(1, -12), (0, -80)]], 2),
                         rrf([[(0, 2), (1, 1)], [(1, 2), (0, 1)]], 2))

    def test_metric_duplicates_consume_rank_without_extra_credit(self):
        result = metrics(["x", "a", "a", "b"], ["a", "b"], 4)
        self.assertEqual(1, result["recall"])
        self.assertEqual(.5, result["mrr"])
        self.assertAlmostEqual((1/math.log2(3)+1/math.log2(5))/(1+1/math.log2(3)), result["ndcg"])
        self.assertEqual(.5, metrics(["a", "a", "x"], ["a", "b"], 3)["recall"])
        self.assertIsNone(metrics(["a"], [], 3))

    def test_offline_path_cannot_call_external_network(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Unexpected network")):
            result = ask(self.retriever, "GPU rezervasyonu kaç saat?", k=3)
            self.assertEqual("evidence_only", result["status"])
            self.assertEqual(0, result["llm_calls"])
            self.assertIn("2 saatlik", result["sources"][0]["context_text"])
            result = ask(self.retriever, "zqxjv plwz")
            self.assertEqual("no_evidence", result["status"])

    def test_evaluation_accounting(self):
        result = evaluate(self.retriever, BASE/"data/queries.jsonl", ["bm25"], "dev", 5)
        summary = result["results"]["bm25"]["summary"]
        self.assertEqual(12, summary["answerable_count"])
        self.assertEqual(4, summary["unanswerable_count"])
        self.assertEqual(0, summary["llm_calls"])
        self.assertLessEqual(summary["recall@5"], 1)


class ProviderTests(unittest.TestCase):
    def test_openai_compatible_http_contract(self):
        payload = {"choices": [{"message": {"content": "İki saat. [S1]"}, "finish_reason": "stop"}]}
        with model_server(payload) as (url, requests):
            result = ask(Retriever(load_corpus(BASE/"data/documents")), "GPU rezervasyonu kaç saat?", client=ChatClient(url, "fixture-model"))
            self.assertEqual("generated", result["status"])
            self.assertEqual("ids_valid_only", result["citation_check"])
            self.assertEqual("/v1/chat/completions", requests[0]["path"])
            self.assertEqual("fixture-model", requests[0]["body"]["model"])
            context = json.loads(requests[0]["body"]["messages"][1]["content"])
            self.assertEqual("S1", context["evidence"][0]["id"])

    def test_invalid_citation_suppresses_generated_answer(self):
        payload = {"choices": [{"message": {"content": "Yanlış iddia [S999]"}}]}
        with model_server(payload) as (url, _):
            result = ask(Retriever(load_corpus(BASE/"data/documents")), "GPU rezervasyonu?", client=ChatClient(url, "fixture"))
            self.assertEqual("citation_error", result["status"])
            self.assertNotIn("Yanlış iddia", result["answer"])

    def test_malformed_error_timeout_and_truncation(self):
        cases = [({}, 200), ({}, 401), ({"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]}, 200)]
        for response, status in cases:
            with model_server(response, status) as (url, _):
                with self.assertRaises(ProviderError):
                    ChatClient(url, "fixture").complete([])
        with model_server({}, delay=.1) as (url, _):
            with self.assertRaises(ProviderError):
                ChatClient(url, "fixture", timeout=.01).complete([])

    def test_hyde_is_only_query_input(self):
        class Fixture:
            model = "fixture"
            def __init__(self): self.messages=[]
            def complete(self, messages, max_tokens=512):
                self.messages.append(messages)
                return "GPU rezervasyonu HYPOTHETICAL_SENTINEL" if len(self.messages) == 1 else "İki saat. [S1]"
        client = Fixture()
        result = ask(Retriever(load_corpus(BASE/"data/documents")), "GPU rezervasyonu?", client=client, hyde=True)
        self.assertEqual(2, result["llm_calls"])
        self.assertNotIn("HYPOTHETICAL_SENTINEL", client.messages[-1][1]["content"])
        self.assertNotIn("HYPOTHETICAL_SENTINEL", json.dumps(result["sources"]))

    def test_decomposition_is_bounded_and_requires_llm(self):
        with self.assertRaises(ValueError):
            plan_queries("iki soru", decompose=True)
        class Fixture:
            def complete(self, *a): return '["alt soru bir", "alt soru iki"]'
        queries, trace, calls = plan_queries("asıl soru", Fixture(), decompose=True)
        self.assertEqual(3, len(queries))
        self.assertEqual(1, calls)
        class Bad:
            def complete(self, *a): return '{"instruction": "bad"}'
        with self.assertRaises(ProviderError):
            plan_queries("soru", Bad(), decompose=True)


class APITests(unittest.TestCase):
    def test_http_ui_retrieval_evaluation_and_validation(self):
        retriever = Retriever(load_corpus(BASE/"data/documents"))
        with serving(make_server(retriever, BASE/"data/queries.jsonl", 0)) as base:
            with urllib.request.urlopen(base) as response:
                self.assertIn(b"RAG Laboratuvar", response.read())
            def post(path, body, headers=None):
                return urllib.request.urlopen(urllib.request.Request(base+path, json.dumps(body).encode(), {"Content-Type":"application/json", **(headers or {})}))
            with post("/api/search", {"question":"GPU rezervasyonu?", "k":3}) as response:
                self.assertEqual(3, len(json.load(response)["hits"]))
            with post("/api/evaluate", {"split":"dev"}) as response:
                self.assertIn("results", json.load(response))
            for body in ({"question":""}, {"question":"GPU", "k":True}, {"question":"GPU", "method":"invalid"}):
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    post("/api/search", body)
                self.assertEqual(400, ctx.exception.code)
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                post("/api/search", {"question":"GPU?"}, {"Origin":"http://other.example"})
            self.assertEqual(403, ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
