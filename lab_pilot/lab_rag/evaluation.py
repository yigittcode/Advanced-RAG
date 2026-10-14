"""Section-level binary qrels, exact evidence checks, negative-query reporting."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import statistics

from .pipeline import retrieve


def metrics(ranked_sections, relevant, k):
    # Same section split into multiple chunks earns relevance credit only once.
    ranked = ranked_sections[:k]
    relevant = set(relevant)
    if not relevant:
        return None
    seen, flags = set(), []
    for section in ranked:
        flags.append(int(section in relevant and section not in seen))
        seen.add(section)
    dcg = sum(v/math.log2(i+2) for i, v in enumerate(flags))
    ideal = sum(1/math.log2(i+2) for i in range(min(k, len(relevant))))
    return {"recall": len(set(ranked)&relevant)/len(relevant),
            "mrr": next((1/(i+1) for i, v in enumerate(flags) if v), 0),
            "ndcg": dcg/ideal, "all_evidence_sections": int(relevant <= set(ranked))}


def load_queries(path, corpus, split):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    sections = {c.section_id for c in corpus.chunks}
    ids = set()
    for row in rows:
        if row["id"] in ids or row["split"] not in ("dev", "test"):
            raise ValueError("Tekrarlanan query ID veya geçersiz split.")
        ids.add(row["id"])
        if not isinstance(row["question"], str) or not row["question"].strip():
            raise ValueError("Boş soru.")
        relevant = row["relevant"]
        if not set(relevant) <= sections:
            raise ValueError(f'{row["id"]}: Corpus içinde bulunmayan relevance etiketi.')
        if set(relevant) != set(row["evidence"]):
            raise ValueError("Her relevant bölüm için bir evidence alıntısı gerekli.")
        for section, phrase in row["evidence"].items():
            if not isinstance(phrase, str) or not phrase or not any(c.section_id == section and phrase in c.text for c in corpus.chunks):
                raise ValueError(f'{row["id"]}: Evidence alıntısı chunk içinde bulunamadı; chunk ayarını/etiketi kontrol edin.')
    chosen = [r for r in rows if split == "all" or r["split"] == split]
    if not chosen:
        raise ValueError("Seçilen split boş.")
    return chosen


def evaluate(retriever, query_path, methods, split="test", k=5, candidates=20, client=None, hyde=False, decompose=False):
    queries = load_queries(query_path, retriever.corpus, split)
    outputs = {}
    for method in methods:
        rows, timings = [], []
        # One untimed warm-up ensures weight loading/indexing is not mixed into latency.
        retriever.search([queries[0]["question"]], method, k, candidates)
        for q in queries:
            result = retrieve(retriever, q["question"], method, k, candidates, client, hyde, decompose)
            hits = result["hits"]
            rank = [h["section_id"] for h in hits]
            values = metrics(rank, q["relevant"], k)
            if values is not None:
                values["evidence_recall"] = sum(any(h["section_id"] == s and phrase in h["text"] for h in hits) for s, phrase in q["evidence"].items())/len(q["relevant"])
            elapsed = sum(result["timing_ms"].values())
            timings.append(elapsed)
            rows.append({"id": q["id"], "question": q["question"], "category": q["category"],
                         "relevant": q["relevant"], "retrieved": [{"section_id": h["section_id"], "chunk_id": h["chunk_id"], "score": h["score"]} for h in hits],
                         "metrics": values, "negative_has_candidates": bool(hits) if not q["relevant"] else None,
                         "latency_ms": elapsed, "llm_calls": result["llm_calls"], "query_trace": result["query_trace"]})
        positives = [r["metrics"] for r in rows if r["metrics"] is not None]
        negatives = [r for r in rows if r["metrics"] is None]
        summary = {f"{key}@{k}": round(statistics.mean(r[key] for r in positives), 4) for key in positives[0]} if positives else {}
        summary.update(answerable_count=len(positives), unanswerable_count=len(negatives),
                       negative_candidate_rate=round(statistics.mean(r["negative_has_candidates"] for r in negatives), 4) if negatives else None,
                       latency_p50_ms=round(statistics.median(timings), 3),
                       latency_p95_ms=round(sorted(timings)[math.ceil(0.95*len(timings))-1], 3),
                       llm_calls=sum(r["llm_calls"] for r in rows))
        outputs[method] = {"summary": summary, "queries": rows}
    code = sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        code.update(path.name.encode()+path.read_bytes())
    return {"schema": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_note": "Synthetic teaching set; dev/test is NOT an independent production benchmark. Retrieval only; no generation accuracy measured.",
            "python": platform.python_version(), "platform": platform.platform(), "code_sha256": code.hexdigest(),
            "corpus_sha256": retriever.corpus.fingerprint, "corpus_files": retriever.corpus.files,
            "queries_sha256": sha256(Path(query_path).read_bytes()).hexdigest(),
            "config": {"split": split, "k": k, "candidates": candidates, "chunk_words": retriever.corpus.chunk_words,
                       "overlap": retriever.corpus.overlap, "chunks": len(retriever.corpus.chunks), "hyde": hyde, "decompose": decompose,
                       "rrf_constant": 60, "dense_device": retriever.dense.device if retriever.dense else None,
                       "e5_prefix": retriever.dense.e5_prefix if retriever.dense else None,
                       "dense_model": retriever.dense.path if retriever.dense else None,
                       "reranker": retriever.reranker.path if retriever.reranker else None,
                       "llm_model": client.model if client else None}, "results": outputs}
