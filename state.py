from typing import TypedDict, Optional


class PipelineState(TypedDict):
    """
    Single state object that flows through every LangGraph node.
    Each node reads what it needs and writes its outputs back here.
    """

    # ── Inputs ──────────────────────────────────────────────
    jd_text:   str          # raw job description text
    pdf_bytes: bytes        # raw PDF bytes of the resume

    # ── Parser output ────────────────────────────────────────
    resume_json: Optional[dict]
    # Shape:
    # {
    #   "name": str,
    #   "skills": [str],
    #   "experience_years": int,
    #   "projects": [{"title": str, "description": str, "tech": [str]}],
    #   "links": {"github": str | None, "linkedin": str | None},
    #   "raw_text": str
    # }

    # ── Similarity node output ───────────────────────────────
    pinecone_matches: Optional[list]
    # Shape per item:
    # {
    #   "resume_chunk": str,
    #   "jd_match":     str,
    #   "cosine":       float   # 0.0 – 1.0
    # }

    # ── Scorer node output ───────────────────────────────────
    score_result: Optional[dict]
    # Shape:
    # {
    #   "exact_score":       int,
    #   "similarity_score":  int,
    #   "achievement_score": int,
    #   "ownership_score":   int,
    #   "overall":           int,
    #   "reasoning": {
    #       "exact":       str,
    #       "similarity":  str,
    #       "achievement": str,
    #       "ownership":   str
    #   },
    #   "red_flags":   [str],
    #   "green_flags": [str]
    # }

    # ── Final report ─────────────────────────────────────────
    final_report: Optional[dict]