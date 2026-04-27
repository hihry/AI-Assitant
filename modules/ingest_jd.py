"""
ingest_jd.py
────────────
Ingests a Job Description into Pinecone.
Run this ONCE per JD before evaluating any resumes against it.

Usage (CLI):
    python ingest_jd.py --jd sample_data/jd_sample.json

Usage (import):
    from ingest_jd import ingest_jd
    ingest_jd(jd_data, jd_id="jd-backend-001")
"""

import argparse
import json
import time
from typing import List, Tuple

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

import config


# ── Singleton model load (slow first time, cached after) ─────────────────────
_embed_model: SentenceTransformer | None = None

def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        print(f"[embed] Loading '{config.EMBED_MODEL}' locally (one-time download ~90MB)...")
        _embed_model = SentenceTransformer(config.EMBED_MODEL)
        print("[embed] Model ready.")
    return _embed_model


# ── Pinecone client ───────────────────────────────────────────────────────────
def get_pinecone_index():
    """Connect to Pinecone and return the index, creating it if it doesn't exist."""
    pc = Pinecone(api_key=config.PINECONE_API_KEY)

    existing = [idx.name for idx in pc.list_indexes()]

    if config.PINECONE_INDEX_NAME not in existing:
        print(f"[pinecone] Index '{config.PINECONE_INDEX_NAME}' not found — creating...")
        pc.create_index(
            name=config.PINECONE_INDEX_NAME,
            dimension=config.PINECONE_DIMENSION,
            metric=config.PINECONE_METRIC,
            spec=ServerlessSpec(
                cloud=config.PINECONE_CLOUD,
                region=config.PINECONE_REGION,
            ),
        )
        # Wait until index is ready
        while not pc.describe_index(config.PINECONE_INDEX_NAME).status["ready"]:
            print("[pinecone] Waiting for index to be ready...")
            time.sleep(2)
        print("[pinecone] Index created and ready.")
    else:
        print(f"[pinecone] Connected to existing index '{config.PINECONE_INDEX_NAME}'.")

    return pc.Index(config.PINECONE_INDEX_NAME)


# ── Chunking ──────────────────────────────────────────────────────────────────
def chunk_jd(jd_data: dict) -> List[Tuple[str, dict]]:
    """
    Convert a JD dict into (text, metadata) chunks.
    Each requirement/responsibility bullet → one chunk.
    Short chunks = precise embeddings = better cosine matches.

    Returns: list of (chunk_text, metadata_dict)
    """
    chunks: List[Tuple[str, dict]] = []
    jd_id = jd_data.get("id", "jd-unknown")

    # Requirements bullets
    for req in jd_data.get("requirements", []):
        chunks.append((
            req.strip(),
            {
                "jd_id":    jd_id,
                "section":  "requirement",
                "text":     req.strip(),
            }
        ))

    # Responsibilities bullets
    for resp in jd_data.get("responsibilities", []):
        chunks.append((
            resp.strip(),
            {
                "jd_id":    jd_id,
                "section":  "responsibility",
                "text":     resp.strip(),
            }
        ))

    # Nice-to-have bullets (lower priority but still useful for similarity)
    for nth in jd_data.get("nice_to_have", []):
        chunks.append((
            nth.strip(),
            {
                "jd_id":    jd_id,
                "section":  "nice_to_have",
                "text":     nth.strip(),
            }
        ))

    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────
def embed_chunks(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of text strings using the local sentence-transformers model.
    Returns a list of float vectors (dim = PINECONE_DIMENSION = 384).
    """
    model = get_embed_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    # normalize_embeddings=True → unit vectors → cosine similarity = dot product
    return embeddings.tolist()


# ── Upsert ────────────────────────────────────────────────────────────────────
def upsert_to_pinecone(index, jd_id: str, chunks: List[Tuple[str, dict]], embeddings: List[List[float]]):
    """
    Upsert (chunk_id, vector, metadata) triples into the JD namespace.
    Pinecone upsert is idempotent — re-running with the same jd_id safely overwrites.
    """
    vectors = []
    for i, ((text, meta), emb) in enumerate(zip(chunks, embeddings)):
        vectors.append({
            "id":       f"{jd_id}-chunk-{i}",
            "values":   emb,
            "metadata": meta,
        })

    # Pinecone recommends batches of ≤100
    batch_size = 100
    for start in range(0, len(vectors), batch_size):
        batch = vectors[start : start + batch_size]
        index.upsert(vectors=batch, namespace=config.JD_NAMESPACE)
        print(f"[pinecone] Upserted {len(batch)} vectors (batch {start // batch_size + 1})")


# ── Main entry point ──────────────────────────────────────────────────────────
def ingest_jd(jd_data: dict, jd_id: str | None = None) -> dict:
    """
    Full ingestion pipeline for one JD.

    Args:
        jd_data: parsed JD dict (see sample_data/jd_sample.json for shape)
        jd_id:   override ID; falls back to jd_data["id"] or "jd-unknown"

    Returns:
        summary dict {jd_id, chunks_ingested, namespace}
    """
    resolved_id = jd_id or jd_data.get("id", "jd-unknown")
    print(f"\n=== Ingesting JD: '{resolved_id}' ===")

    # 1. Connect to Pinecone
    index = get_pinecone_index()

    # 2. Chunk the JD
    chunks = chunk_jd(jd_data)
    texts  = [c[0] for c in chunks]
    print(f"[chunk] Split JD into {len(chunks)} chunks.")

    # 3. Embed locally
    print("[embed] Embedding chunks...")
    embeddings = embed_chunks(texts)
    print(f"[embed] Done. Vector dim = {len(embeddings[0])}")

    # 4. Upsert to Pinecone
    upsert_to_pinecone(index, resolved_id, chunks, embeddings)

    summary = {
        "jd_id":            resolved_id,
        "chunks_ingested":  len(chunks),
        "namespace":        config.JD_NAMESPACE,
    }
    print(f"\n✓ Ingestion complete: {summary}")
    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a JD JSON file into Pinecone.")
    parser.add_argument("--jd", required=True, help="Path to JD JSON file")
    parser.add_argument("--id", default=None,  help="Override JD ID (optional)")
    args = parser.parse_args()

    with open(args.jd, "r") as f:
        jd_data = json.load(f)

    ingest_jd(jd_data, jd_id=args.id)