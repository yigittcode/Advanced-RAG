"""Inspectable retrieval baseline; only the Python standard library is required."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import unicodedata


STOP = set("ve veya ile bir bu su o da de icin mi mu ne nasil nedir kac hangi olarak gore the a an is are of to in and what how".split())
METHODS = ("bm25", "lexical", "dense", "hybrid")


def normalize(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı").lower()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", normalize(text)) if t not in STOP and len(t) > 1]


def chargrams(text: str) -> list[str]:
    # Lexical tolerance for Turkish suffixes/typos; this is NOT semantic embedding.
    return [word[i:i+3] for word in tokens(text) for i in range(len(word)-2)]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    section_id: str
    source: str
    title: str
    text: str
    start_line: int
    end_line: int


@dataclass
class Corpus:
    chunks: list[Chunk]
    fingerprint: str
    files: list[dict]
    chunk_words: int
    overlap: int


def load_corpus(root: Path, chunk_words: int = 110, overlap: int = 20) -> Corpus:
    if not 20 <= chunk_words <= 1000 or not 0 <= overlap < chunk_words:
        raise ValueError("chunk_words 20..1000 olmalı; 0 <= overlap < chunk_words.")
    if not root.is_dir():
        raise ValueError(f"Belge dizini bulunamadı: {root}")
    chunks, files, seen_sections = [], [], set()
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in (".md", ".txt") or not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Corpus içindeki sembolik bağlantılar desteklenmiyor.")
        if path.stat().st_size > 2_000_000:
            raise ValueError(f"2 MB belge sınırı aşıldı: {path.name}")
        text = path.read_text(encoding="utf-8")
        source = path.relative_to(root).as_posix()
        files.append({"source": source, "sha256": sha256(text.encode()).hexdigest()})
        headings = list(re.finditer(r"^#{2,6}\s+(.+)$", text, re.M))
        sections = []
        if headings:
            for i, h in enumerate(headings):
                title = h.group(1).strip()
                # Explicit 'id | title' makes labels stable when prose changes.
                label = title.split("|", 1)[0].strip()
                slug = re.sub(r"[^a-z0-9]+", "-", normalize(label)).strip("-")
                end = headings[i+1].start() if i+1 < len(headings) else len(text)
                sections.append((slug, title, h.end(), end))
        else:
            sections = [("document", path.stem, 0, len(text))]
        for slug, title, start, end in sections:
            section_id = f"{source}#{slug}"
            if not slug or section_id in seen_sections:
                raise ValueError(f"Boş/tekrarlanan bölüm kimliği: {section_id}")
            seen_sections.add(section_id)
            words = list(re.finditer(r"\S+", text[start:end]))
            for offset in range(0, len(words), chunk_words-overlap):
                window = words[offset:offset+chunk_words]
                a, b = start+window[0].start(), start+window[-1].end()
                body = text[a:b]
                identity = f"{section_id}:{offset}:{body}"
                chunks.append(Chunk(
                    sha256(identity.encode()).hexdigest()[:20], section_id, source, title,
                    body, text.count("\n", 0, a)+1, text.count("\n", 0, b)+1,
                ))
                if offset+chunk_words >= len(words):
                    break
    if not chunks:
        raise ValueError("İndekslenecek UTF-8 .md/.txt belgesi yok.")
    fingerprint = sha256(json.dumps({"files": files, "words": chunk_words, "overlap": overlap}, sort_keys=True).encode()).hexdigest()
    return Corpus(chunks, fingerprint, files, chunk_words, overlap)


class BM25:
    def __init__(self, documents: list[str], tokenize=tokens):
        self.tokenize = tokenize
        self.rows = [Counter(tokenize(d)) for d in documents]
        self.lengths = [sum(row.values()) for row in self.rows]
        self.avg = sum(self.lengths)/len(self.rows) or 1
        df = Counter(t for row in self.rows for t in row)
        self.idf = {t: math.log(1+(len(self.rows)-n+0.5)/(n+0.5)) for t, n in df.items()}

    def search(self, query: str, limit: int) -> list[tuple[int, float]]:
        q = set(self.tokenize(query))
        scored = []
        for i, row in enumerate(self.rows):
            score = sum(self.idf.get(t, 0)*row[t]*2.5/(row[t]+1.5*(0.25+0.75*self.lengths[i]/self.avg)) for t in q if row[t])
            if score > 0:
                scored.append((i, score))
        return sorted(scored, key=lambda x: (-x[1], x[0]))[:limit]


def rrf(rankings: list[list[tuple[int, float]]], limit: int, constant: int = 60) -> list[tuple[int, float]]:
    scores: Counter = Counter()
    for ranking in rankings:
        seen = set()
        for rank, (index, _) in enumerate(ranking, 1):
            if index not in seen:
                scores[index] += 1/(constant+rank)
                seen.add(index)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:limit]


class Retriever:
    def __init__(self, corpus: Corpus, dense=None, reranker=None):
        self.corpus, self.dense, self.reranker = corpus, dense, reranker
        self.documents = [f"{c.title}\n{c.text}" for c in corpus.chunks]
        self.word = BM25(self.documents)
        self.char = BM25(self.documents, chargrams)

    def search(self, queries: list[str], method: str = "bm25", k: int = 5, candidates: int = 20) -> list[dict]:
        if method not in METHODS or not 1 <= k <= candidates <= 100:
            raise ValueError("Yöntem geçersiz veya 1 <= k <= candidates <= 100 sağlanmıyor.")
        if not queries or len(queries) > 8 or any(not q.strip() or len(q) > 4000 for q in queries):
            raise ValueError("1..8 boş olmayan sorgu gerekli (en fazla 4000 karakter).")
        if method in ("dense", "hybrid") and self.dense is None:
            raise ValueError("Dense/hybrid için --embedding-model ile yerel model dizini gerekli.")
        rankings = []
        for query in queries:
            word = self.word.search(query, candidates)
            if method == "bm25":
                ranked = word
            elif method == "lexical":
                ranked = rrf([word, self.char.search(query, candidates)], candidates)
            else:
                dense = self.dense.search(query, self.documents, candidates)
                ranked = dense if method == "dense" else rrf([word, dense], candidates)
            rankings.append(ranked)
        ranking = rankings[0] if len(rankings) == 1 else rrf(rankings, candidates)
        hits = [{**asdict(self.corpus.chunks[i]), "score": round(float(score), 6)} for i, score in ranking]
        if self.reranker and hits:
            hits = self.reranker.rank(queries[0], hits)
        return hits[:k]
