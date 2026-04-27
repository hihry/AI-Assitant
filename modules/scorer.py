"""
scorer.py
─────────
LangGraph Node 3: ResumeJSON + JD + similarity_score → full 4D ScoreResult

Pipeline position:
    parse_resume → similarity_search → [scorer] → build_report

What it does:
    1. Reads resume_json + jd_text + existing score_result (has similarity_score from Pinecone)
    2. Builds a structured prompt with resume vs JD content
    3. Calls Groq (llama-3.3-70b-versatile) to compute:
           - Exact Score:       hard keyword overlap
           - Achievement Score: quantified impact detection
           - Ownership Score:   strong vs weak verb analysis
    4. Merges Pinecone's similarity_score with the 3 LLM scores
    5. Computes weighted overall score using config.SCORE_WEIGHTS
    6. Attaches full reasoning + red/green flags for explainability
    7. Writes complete score_result back to PipelineState
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

from groq import Groq

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from state import PipelineState


# ── Groq client (singleton) ───────────────────────────────────────────────────
_groq_client: Groq | None = None

def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


# ── Prompt builder ────────────────────────────────────────────────────────────
def build_score_prompt(resume_json: dict, jd_data: dict) -> str:
    """
    Populate the score_candidate.txt prompt template with resume + JD content.
    Formats projects into readable bullet strings for the LLM.
    """

    project_root = Path(__file__).resolve().parent.parent
    prompt_path = project_root / "prompts" / "score_candidate.txt"
    template    = prompt_path.read_text(encoding="utf-8")

    # Format projects as readable text block
    project_lines = []
    for p in resume_json.get("projects", []):
        title        = p.get("title", "Untitled")
        description  = p.get("description", "")
        tech         = ", ".join(p.get("tech", []))
        own_verbs    = ", ".join(p.get("ownership_verbs", []))
        achievements = p.get("achievement_bullets", [])

        project_lines.append(f"  Project/Role: {title}")
        if description:
            project_lines.append(f"    Summary: {description}")
        if tech:
            project_lines.append(f"    Tech: {tech}")
        if own_verbs:
            project_lines.append(f"    Action verbs used: {own_verbs}")
        for ab in achievements:
            project_lines.append(f"    Achievement: {ab}")
        project_lines.append("")

    # Format JD sections
    requirements     = "\n".join(f"  - {r}" for r in jd_data.get("requirements", []))
    responsibilities = "\n".join(f"  - {r}" for r in jd_data.get("responsibilities", []))

    return (
        template
        .replace("{jd_requirements}",    requirements)
        .replace("{jd_responsibilities}", responsibilities)
        .replace("{candidate_name}",     resume_json.get("name", "Unknown"))
        .replace("{experience_years}",   str(resume_json.get("experience_years", 0)))
        .replace("{skills}",             ", ".join(resume_json.get("skills", [])))
        .replace("{projects}",           "\n".join(project_lines))
    )


# ── JSON extraction (robust) ──────────────────────────────────────────────────
def extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    start   = cleaned.find("{")
    end     = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response:\n{raw[:400]}")
    return json.loads(cleaned[start:end])


# ── Score validation ──────────────────────────────────────────────────────────
def clamp(value: Any, lo: int = 0, hi: int = 100) -> int:
    """Ensure a score is an integer in [0, 100]."""
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return 0


def validate_llm_scores(parsed: dict) -> dict:
    """
    Guarantee required keys exist and scores are valid integers.
    Prevents downstream KeyErrors if the LLM omits a field.
    """
    parsed["exact_score"]       = clamp(parsed.get("exact_score", 0))
    parsed["achievement_score"] = clamp(parsed.get("achievement_score", 0))
    parsed["ownership_score"]   = clamp(parsed.get("ownership_score", 0))

    if "reasoning" not in parsed or not isinstance(parsed["reasoning"], dict):
        parsed["reasoning"] = {}
    parsed["reasoning"].setdefault("exact",       "No reasoning provided.")
    parsed["reasoning"].setdefault("achievement",  "No reasoning provided.")
    parsed["reasoning"].setdefault("ownership",    "No reasoning provided.")

    parsed.setdefault("red_flags",   [])
    parsed.setdefault("green_flags", [])

    return parsed


# ── Weighted overall score ────────────────────────────────────────────────────
def compute_overall(scores: dict) -> int:
    """
    Weighted average of all four dimensions using config.SCORE_WEIGHTS.
    Weights: exact=0.30, similarity=0.35, achievement=0.20, ownership=0.15
    """
    w = config.SCORE_WEIGHTS
    overall = (
        scores["exact_score"]       * w["exact"]       +
        scores["similarity_score"]  * w["similarity"]  +
        scores["achievement_score"] * w["achievement"] +
        scores["ownership_score"]   * w["ownership"]
    )
    return round(overall)


# ── Core function ─────────────────────────────────────────────────────────────
def run_scorer(resume_json: dict, jd_data: dict, similarity_score: int,
               similarity_matches: list) -> dict:
    """
    Run the full scoring pipeline for one resume.

    Args:
        resume_json:        parsed resume from parse_resume node
        jd_data:            parsed JD dict (from jd_sample.json or UI input)
        similarity_score:   already computed by Pinecone in similarity node
        similarity_matches: raw match list for embedding in reasoning

    Returns:
        Complete score_result dict ready for build_report node.
    """
    print("[scorer] Building prompt...")
    prompt = build_score_prompt(resume_json, jd_data)

    print("[scorer] Calling Groq for Exact / Achievement / Ownership scores...")
    client   = get_groq_client()
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise technical recruiter scoring system. "
                    "You ALWAYS respond with only a valid JSON object. "
                    "No markdown, no explanation outside the JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=1500,
    )

    raw_output = response.choices[0].message.content
    print("[scorer] Received response. Parsing JSON...")

    try:
        llm_scores = extract_json(raw_output)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"[scorer] Failed to parse LLM JSON: {e}\n\nRaw:\n{raw_output[:500]}")

    llm_scores = validate_llm_scores(llm_scores)

    # ── Merge similarity score from Pinecone ──────────────────────────────────
    llm_scores["similarity_score"] = similarity_score

    # Build a human-readable similarity reasoning string from Pinecone matches
    sim_reasoning_lines = []
    for m in similarity_matches[:5]:
        sim_reasoning_lines.append(
            f"'{m['resume_chunk']}' → '{m['jd_match'][:60]}' (cosine: {m['cosine']:.2f})"
        )
    llm_scores["reasoning"]["similarity"] = (
        f"Pinecone vector search found {len(similarity_matches)} JD requirement matches. "
        f"Top matches:\n" + "\n".join(sim_reasoning_lines)
    )

    # ── Compute weighted overall ──────────────────────────────────────────────
    llm_scores["overall"] = compute_overall(llm_scores)

    # ── Determine tier ────────────────────────────────────────────────────────
    overall = llm_scores["overall"]
    if overall >= config.TIER_THRESHOLDS["A"]:
        llm_scores["tier"] = "A"
    elif overall >= config.TIER_THRESHOLDS["B"]:
        llm_scores["tier"] = "B"
    else:
        llm_scores["tier"] = "C"

    # ── Keep similarity matches for report rendering ──────────────────────────
    llm_scores["similarity_matches"] = similarity_matches

    # ── Print summary ─────────────────────────────────────────────────────────
    w = config.SCORE_WEIGHTS
    print(f"\n[scorer] ✓ Scoring complete for '{resume_json.get('name', 'Unknown')}'")
    print(f"  Exact       ({int(w['exact']*100)}%): {llm_scores['exact_score']:>3}/100")
    print(f"  Similarity  ({int(w['similarity']*100)}%): {llm_scores['similarity_score']:>3}/100  ← Pinecone")
    print(f"  Achievement ({int(w['achievement']*100)}%): {llm_scores['achievement_score']:>3}/100")
    print(f"  Ownership   ({int(w['ownership']*100)}%): {llm_scores['ownership_score']:>3}/100")
    print(f"  ─────────────────────")
    print(f"  Overall:          {llm_scores['overall']:>3}/100  (Tier {llm_scores['tier']})")

    return llm_scores


# ── LangGraph node wrapper ────────────────────────────────────────────────────
def scorer_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node. Reads resume_json + score_result (similarity) + jd_text.
    Writes complete score_result back to state.
    """
    import json as _json

    # jd_text may be raw string or JSON string — normalise to dict
    jd_raw = state.get("jd_text", "{}")
    try:
        jd_data = _json.loads(jd_raw) if isinstance(jd_raw, str) else jd_raw
    except _json.JSONDecodeError:
        # Fallback: treat as plain text, wrap in minimal dict
        jd_data = {"requirements": [jd_raw], "responsibilities": []}

    existing      = state.get("score_result", {}) or {}
    sim_score     = existing.get("similarity_score", 0)
    sim_matches   = existing.get("similarity_matches", [])

    score_result = run_scorer(
        resume_json       = state["resume_json"],
        jd_data           = jd_data,
        similarity_score  = sim_score,
        similarity_matches= sim_matches,
    )

    return {**state, "score_result": score_result}


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    mock_resume = {
        "name": "Arjun Mehta",
        "experience_years": 5,
        "skills": [
            "Python", "Go", "TypeScript", "FastAPI", "Django",
            "PostgreSQL", "Redis", "AWS Kinesis", "Docker", "Terraform",
            "GitHub Actions", "Jenkins", "gRPC",
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
            {
                "title": "Redis Caching Layer",
                "description": "Architected Redis caching layer that cut database load by 45%",
                "tech": ["Redis", "Python"],
                "ownership_verbs": ["architected"],
                "achievement_bullets": ["cut database load by 45%"],
            },
            {
                "title": "REST API Platform",
                "description": "Owned end-to-end design of REST APIs serving 500K daily active users",
                "tech": ["FastAPI", "PostgreSQL"],
                "ownership_verbs": ["owned"],
                "achievement_bullets": ["serving 500K daily active users"],
            },
        ],
        "raw_text": "",
    }

    with open("sample_data/jd_sample.json", encoding="utf-8") as f:
        jd_data = json.load(f)

    # Mock similarity already computed by Pinecone
    mock_sim_score   = 84
    mock_sim_matches = [
        {"resume_chunk": "AWS Kinesis", "jd_match": "Experience with Apache Kafka or similar message queues (RabbitMQ, AWS Kinesis)", "cosine": 0.91},
        {"resume_chunk": "PostgreSQL",  "jd_match": "Proficiency with PostgreSQL and Redis",                                          "cosine": 0.95},
        {"resume_chunk": "Docker",      "jd_match": "Experience with Docker and Kubernetes",                                          "cosine": 0.88},
        {"resume_chunk": "Terraform",   "jd_match": "Experience with Terraform or similar IaC tools",                                 "cosine": 0.93},
        {"resume_chunk": "Python",      "jd_match": "Strong proficiency in Python or Go",                                             "cosine": 0.97},
    ]

    result = run_scorer(mock_resume, jd_data, mock_sim_score, mock_sim_matches)
    print("\n── Full Score Result ────────────────────────────")
    print(json.dumps(result, indent=2))