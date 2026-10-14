"""Optional inference adapters. No OpenAI SDK, auto-downloads, or API defaults."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import socket
import urllib.error
import urllib.parse
import urllib.request


class ProviderError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Do not forward credentials or documents to another host.


class ChatClient:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 30):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("RAG_LLM_BASE_URL geçerli http(s) adresi olmalı; credentials/query içermemeli.")
        if not model.strip() or not 0 < timeout <= 120:
            raise ValueError("RAG_LLM_MODEL ve 0 < timeout <= 120 gerekli.")
        self.url = base_url.rstrip("/")+"/chat/completions"
        self.model, self.api_key, self.timeout = model, api_key, timeout

    @classmethod
    def from_env(cls):
        url, model = os.getenv("RAG_LLM_BASE_URL", ""), os.getenv("RAG_LLM_MODEL", "")
        if not url or not model:
            raise ValueError("--llm için RAG_LLM_BASE_URL ve RAG_LLM_MODEL ayarlayın; otomatik bulut bağlantısı yok.")
        return cls(url, model, os.getenv("RAG_LLM_API_KEY", ""), float(os.getenv("RAG_LLM_TIMEOUT", "30")))

    def complete(self, messages: list[dict], max_tokens: int = 512) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer "+self.api_key
        payload = json.dumps({"model": self.model, "messages": messages, "temperature": 0,
                              "max_tokens": max_tokens, "stream": False}).encode()
        request = urllib.request.Request(self.url, payload, headers, method="POST")
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ProviderError("Model yanıtı boyut sınırını aştı.")
            data = json.loads(raw)
            choice = data["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ProviderError("Model yanıtı token sınırında kesildi; model bütçesini kontrol edin.")
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")
            return content.strip()
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"LLM HTTP {exc.code}; endpoint/model/anahtar ayarını kontrol edin.") from None
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            raise ProviderError("LLM bağlantısı kurulamadı veya zaman aşımına uğradı.") from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderError("LLM geçerli Chat Completions metin yanıtı döndürmedi.") from None


def _local_path(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise ValueError("Model önce yerel dizine indirilmeli; model hub adı kabul edilmiyor.")
    return str(p)


class LocalDense:
    def __init__(self, path: str, device: str = "cpu", e5_prefix: bool = True):
        self.path = _local_path(path)
        self.device, self.e5_prefix = device, e5_prefix
        self.model, self.vectors, self.document_key = None, None, None

    def search(self, query: str, documents: list[str], limit: int):
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ProviderError("Dense için requirements-models.txt paketlerini kurun.") from None
            self.model = SentenceTransformer(self.path, device=self.device, local_files_only=True, trust_remote_code=False)
        key = tuple(documents)
        if key != self.document_key:
            passages = [("passage: " if self.e5_prefix else "")+d for d in documents]
            self.vectors = self.model.encode(passages, batch_size=8, normalize_embeddings=True, show_progress_bar=False)
            self.document_key = key
        q = self.model.encode([("query: " if self.e5_prefix else "")+query], normalize_embeddings=True, show_progress_bar=False)[0]
        scores = self.vectors @ q
        if not all(math.isfinite(float(v)) for v in scores):
            raise ProviderError("Embedding sonlu olmayan skor üretti.")
        return sorted(enumerate(map(float, scores)), key=lambda x: (-x[1], x[0]))[:limit]


class LocalReranker:
    def __init__(self, path: str, device: str = "cpu"):
        self.path, self.device, self.model = _local_path(path), device, None

    def rank(self, query: str, hits: list[dict]) -> list[dict]:
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError:
                raise ProviderError("Reranker için requirements-models.txt paketlerini kurun.") from None
            self.model = CrossEncoder(self.path, device=self.device, local_files_only=True, trust_remote_code=False)
        scores = self.model.predict([(query, h["text"]) for h in hits], show_progress_bar=False)
        if len(scores) != len(hits) or not all(math.isfinite(float(v)) for v in scores):
            raise ProviderError("Reranker tekil, sonlu skorlar döndürmeli.")
        ranked = [{**h, "rerank_score": float(s)} for h, s in zip(hits, scores)]
        # Do not add raw logits to BM25/cosine scores; their scales differ.
        return sorted(ranked, key=lambda h: -h["rerank_score"])
