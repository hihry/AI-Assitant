"""
similarity.py
─────────────
LangGraph Node 2: ResumeJSON → Pinecone query → cosine match results

Pipeline position:
    parse_resume → [similarity_search] → scorer → build_report

What it does:
    1. Builds searchable chunks from resume (skills + project tech + descriptions)
    2. Embeds each chunk locally using sentence-transformers (zero API cost)
    3. Queries Pinecone against the jd-requirements namespace for each chunk
    4. Deduplicates and ranks matches by cosine score
    5. Computes similarity_score (0-100) as weighted average of top matches
    6. Writes pinecone_matches + partial score_result into PipelineState
"""

import sys
from pathlib import Path
from typing import List

from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Allow running from project root or modules/
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from state import PipelineState


# ── Singleton embed model (shared with ingest_jd) ────────────────────────────
_embed_model: SentenceTransformer | None = None

def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        print(f"[similarity] Loading '{config.EMBED_MODEL}'...")
        _embed_model = SentenceTransformer(config.EMBED_MODEL)
    return _embed_model


# ── Pinecone client ───────────────────────────────────────────────────────────
def get_pinecone_index():
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    return pc.Index(config.PINECONE_INDEX_NAME)


# ── Resume chunk builder ──────────────────────────────────────────────────────
def build_resume_chunks(resume_json: dict) -> List[dict]:
    """
    Convert resume_json into a flat list of searchable chunks.
    Each chunk is a short, focused string — same strategy as JD chunking.

    Chunk sources (in priority order):
        1. Individual skills  →  "Python", "AWS Kinesis", "Docker"
        2. Project tech tags  →  "AWS Kinesis, SQS"  (joined per project)
        3. Project descriptions  →  one sentence summaries
        4. Raw skills section  →  verbatim fallback if structured skills are thin

    Returns list of {"text": str, "source": str} dicts.
    """
    chunks = []

    # 1. Individual skills — most precise for exact tech matching
    for skill in resume_json.get("skills", []):
        if skill and skill.strip():
            chunks.append({"text": skill.strip(), "source": "skill"})

    # 2. Per-project tech stacks joined — captures tech combos
    for project in resume_json.get("projects", []):
        tech_list = project.get("tech", [])
        if tech_list:
            combined = ", ".join(tech_list)
            chunks.append({
                "text":   combined,
                "source": f"project_tech:{project.get('title', 'untitled')}",
            })

    # 3. Project descriptions — captures responsibilities-level semantics
    for project in resume_json.get("projects", []):
        desc = project.get("description", "").strip()
        if desc:
            chunks.append({
                "text":   desc,
                "source": f"project_desc:{project.get('title', 'untitled')}",
            })

    # 4. Raw skills section as a fallback chunk
    raw = resume_json.get("raw_skills_section")
    if raw and raw.strip():
        chunks.append({"text": raw.strip(), "source": "raw_skills"})

    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────
def embed_chunks(texts: List[str]) -> List[List[float]]:
    model = get_embed_model()
    vecs  = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist()


# ── Pinecone query ────────────────────────────────────────────────────────────
def query_pinecone(index, vector: List[float], top_k: int = 3) -> List[dict]:
    """
    Query Pinecone for the top_k closest JD requirement chunks.
    Returns list of {text, section, cosine} dicts.
    """
    result = index.query(
        vector=vector,
        top_k=top_k,
        namespace=config.JD_NAMESPACE,
        include_metadata=True,
    )
    matches = []
    for m in result.matches:
        matches.append({
            "text":    m.metadata.get("text", ""),
            "section": m.metadata.get("section", ""),
            "cosine":  round(float(m.score), 4),
        })
    return matches


# ── Deduplication ─────────────────────────────────────────────────────────────
def deduplicate_matches(all_matches: List[dict]) -> List[dict]:
    """
    If the same JD requirement text appears multiple times across resume chunks,
    keep only the highest-scoring occurrence.
    """
    best: dict[str, dict] = {}
    for m in all_matches:
        key = m["jd_match"]
        if key not in best or m["cosine"] > best[key]["cosine"]:
            best[key] = m
    # Sort descending by cosine
    return sorted(best.values(), key=lambda x: x["cosine"], reverse=True)


# ── Similarity score computation ──────────────────────────────────────────────
def compute_similarity_score(matches: List[dict]) -> int:
    """
    Compute a 0-100 similarity score from the deduplicated match list.

    Strategy:
        - Top 5 matches get full weight (captures the strongest skill alignments)
        - Score = average cosine of top-5 × 100
        - Cosine is already 0-1 (unit vectors from normalize_embeddings=True)
    """
    if not matches:
        return 0
    top = matches[:5]
    avg_cosine = sum(m["cosine"] for m in top) / len(top)
    return min(100, int(avg_cosine * 100))


# ── Core function ─────────────────────────────────────────────────────────────
def run_similarity_search(resume_json: dict) -> tuple[list, int]:
    """
    Full similarity search for one resume against the indexed JD.

    Returns:
        (pinecone_matches, similarity_score)
        pinecone_matches shape:
        [
          {
            "resume_chunk": str,    # resume skill/tech that was queried
            "resume_source": str,   # where in the resume it came from
            "jd_match": str,        # matched JD requirement text
            "jd_section": str,      # requirement / responsibility / nice_to_have
            "cosine": float         # cosine similarity 0.0-1.0
          },
          ...
        ]
    """
    print("[similarity] Building resume chunks...")
    chunks = build_resume_chunks(resume_json)
    texts  = [c["text"] for c in chunks]
    print(f"[similarity] {len(chunks)} chunks built from resume.")

    if not chunks:
        print("[similarity] Warning: no chunks extracted from resume.")
        return [], 0

    print("[similarity] Embedding resume chunks locally...")
    embeddings = embed_chunks(texts)

    print("[similarity] Querying Pinecone...")
    index = get_pinecone_index()

    raw_matches = []
    for chunk, emb in zip(chunks, embeddings):
        top_matches = query_pinecone(index, emb, top_k=1)  # top-1 per chunk
        if top_matches:
            best = top_matches[0]
            raw_matches.append({
                "resume_chunk":  chunk["text"],
                "resume_source": chunk["source"],
                "jd_match":      best["text"],
                "jd_section":    best["section"],
                "cosine":        best["cosine"],
            })

    # Deduplicate so each JD requirement appears only once (highest score wins)
    deduped = deduplicate_matches(raw_matches)

    score = compute_similarity_score(deduped)

    # Log the key matches for visibility
    print(f"\n[similarity] Top matches:")
    for m in deduped[:6]:
        bar = "█" * int(m["cosine"] * 20)
        print(f"  {m['cosine']:.2f} {bar:<20}  '{m['resume_chunk']}' → '{m['jd_match'][:60]}'")
    print(f"\n[similarity] ✓ Similarity score: {score}/100  ({len(deduped)} unique JD matches)")

    return deduped, score


# ── LangGraph node wrapper ────────────────────────────────────────────────────
def similarity_search_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node. Reads resume_json, writes pinecone_matches + partial score_result.
    """
    matches, sim_score = run_similarity_search(state["resume_json"])

    # Initialise score_result with the similarity component
    # scorer_node will add exact, achievement, ownership later
    score_result = {
        "similarity_score": sim_score,
        "similarity_matches": matches,   # kept for explainability in report
    }

    return {
        **state,
        "pinecone_matches": matches,
        "score_result":     score_result,
    }


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    # Use a mock resume_json so this can be tested without a PDF
    mock_resume = {
        "name": "Arjun Mehta",
        "experience_years": 5,
        "skills": [
            "Python", "Go", "TypeScript",
            "FastAPI", "Django", "gRPC",
            "PostgreSQL", "Redis", "MongoDB",
            "AWS Kinesis", "SQS",
            "Docker", "Terraform",
            "GitHub Actions", "Jenkins",
        ],
        "projects": [
            {
                "title": "Real-time Streaming Pipeline",
                "description": "Built a real-time event streaming pipeline using AWS Kinesis processing 2M events/day",
                "tech": ["AWS Kinesis", "Python", "PostgreSQL"],
                "ownership_verbs": ["built"],
                "achievement_bullets": ["processing 2M events/day"],
            },
            {
                "title": "Microservices Migration",
                "description": "Led migration from monolith to microservices reducing deployment time by 60%",
                "tech": ["Docker", "FastAPI", "GitHub Actions"],
                "ownership_verbs": ["led"],
                "achievement_bullets": ["reducing deployment time by 60%"],
            },
        ],
        "links": {"github": "github.com/arjunmehta", "linkedin": None},
        "raw_skills_section": "Python, Go, FastAPI, PostgreSQL, Redis, AWS Kinesis, Docker, Terraform",
        "raw_text": "",
    }

    matches, score = run_similarity_search(mock_resume)
    print("\n── Full match list ──────────────────────────────")
    print(json.dumps(matches, indent=2))
    print(f"\nFinal similarity score: {score}/100")