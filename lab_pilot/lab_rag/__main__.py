import argparse
import json
from pathlib import Path
import sys

from .core import METHODS, Retriever, load_corpus
from .evaluation import evaluate
from .pipeline import ask
from .providers import ChatClient, LocalDense, LocalReranker, ProviderError

BASE = Path(__file__).resolve().parents[1]


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--corpus", type=Path, default=BASE/"data/documents")
    common.add_argument("--queries", type=Path, default=BASE/"data/queries.jsonl")
    common.add_argument("--chunk-words", type=int, default=110)
    common.add_argument("--overlap", type=int, default=20)
    common.add_argument("--embedding-model", help="Yerel E5/SentenceTransformer model dizini; otomatik indirme yok")
    common.add_argument("--reranker-model", help="Yerel CrossEncoder model dizini")
    common.add_argument("--device", default="cpu")
    common.add_argument("--no-e5-prefix", action="store_true")
    common.add_argument("--llm", action="store_true", help="Yapılandırılmış Chat Completions endpoint'ini kullan")
    common.add_argument("--hyde", action="store_true")
    common.add_argument("--decompose", action="store_true")
    parser = argparse.ArgumentParser(description="Advanced-RAG bağımsız laboratuvar pilotu")
    commands = parser.add_subparsers(dest="command", required=True)
    query = commands.add_parser("ask", parents=[common])
    query.add_argument("question")
    query.add_argument("--method", choices=METHODS, default="bm25")
    query.add_argument("-k", type=int, default=5)
    query.add_argument("--candidates", type=int, default=20)
    query.add_argument("--output", type=Path)
    ev = commands.add_parser("evaluate", parents=[common])
    ev.add_argument("--methods", nargs="+", choices=METHODS, default=["bm25", "lexical"])
    ev.add_argument("--split", choices=["dev", "test", "all"], default="test")
    ev.add_argument("-k", type=int, default=5)
    ev.add_argument("--candidates", type=int, default=20)
    ev.add_argument("--output", type=Path)
    serve = commands.add_parser("serve", parents=[common])
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        if (args.hyde or args.decompose) and not args.llm:
            raise ValueError("--hyde/--decompose için --llm gerekli.")
        corpus = load_corpus(args.corpus, args.chunk_words, args.overlap)
        dense = LocalDense(args.embedding_model, args.device, not args.no_e5_prefix) if args.embedding_model else None
        reranker = LocalReranker(args.reranker_model, args.device) if args.reranker_model else None
        retriever = Retriever(corpus, dense, reranker)
        client = ChatClient.from_env() if args.llm else None
        if args.command == "serve":
            from .server import make_server
            server = make_server(retriever, args.queries, args.port, client, args.hyde, args.decompose)
            print(f"Pilot: http://127.0.0.1:{server.server_port} | {len(corpus.chunks)} parça | {'LLM' if client else 'kaynak gösterimi'}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        if args.command == "ask":
            result = ask(retriever, args.question, args.method, args.k, args.candidates, client, args.hyde, args.decompose)
        else:
            result = evaluate(retriever, args.queries, args.methods, args.split, args.k, args.candidates, client, args.hyde, args.decompose)
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text+"\n", encoding="utf-8")
        print(text)
        return 0
    except (ValueError, ProviderError, OSError) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
