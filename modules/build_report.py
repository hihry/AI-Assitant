"""
build_report.py
───────────────
LangGraph Node 4: score_result + resume_json → final_report

Pipeline position:
    parse_resume → similarity_search → scorer → [build_report]

What it does:
    Assembles every upstream output into one clean, renderer-ready dict.
    This is what the Streamlit UI reads — nothing else touches state directly.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from state import PipelineState


def build_report_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node. Reads resume_json + score_result, writes final_report.
    """
    resume = state.get("resume_json", {})
    scores = state.get("score_result", {})

    reasoning  = scores.get("reasoning", {})
    sim_matches = scores.get("similarity_matches", [])

    # ── Score breakdown with weights for display ──────────────────────────────
    score_breakdown = [
        {
            "dimension": "Exact Match",
            "score":     scores.get("exact_score", 0),
            "weight":    "30%",
            "reasoning": reasoning.get("exact", ""),
        },
        {
            "dimension": "Semantic Similarity",
            "score":     scores.get("similarity_score", 0),
            "weight":    "35%",
            "source":    "Pinecone vector search",
            "reasoning": reasoning.get("similarity", ""),
        },
        {
            "dimension": "Achievement",
            "score":     scores.get("achievement_score", 0),
            "weight":    "20%",
            "reasoning": reasoning.get("achievement", ""),
        },
        {
            "dimension": "Ownership",
            "score":     scores.get("ownership_score", 0),
            "weight":    "15%",
            "reasoning": reasoning.get("ownership", ""),
        },
    ]

    # ── Top similarity matches (for display table) ────────────────────────────
    top_matches = [
        {
            "resume_skill": m.get("resume_chunk", ""),
            "jd_requirement": m.get("jd_match", ""),
            "cosine": m.get("cosine", 0.0),
            "section": m.get("jd_section", ""),
        }
        for m in sim_matches[:8]   # show top 8 in UI
    ]

    # ── Final report dict ─────────────────────────────────────────────────────
    final_report = {
        # Candidate info
        "candidate_name":     resume.get("name", "Unknown"),
        "candidate_email":    resume.get("email"),
        "experience_years":   resume.get("experience_years", 0),
        "skills":             resume.get("skills", []),
        "github":             resume.get("links", {}).get("github"),
        "linkedin":           resume.get("links", {}).get("linkedin"),

        # Verdict
        "overall_score":      scores.get("overall", 0),
        "tier":               scores.get("tier", "C"),
        "tier_label": {
            "A": "Strong Hire",
            "B": "Potential Hire",
            "C": "No Hire",
        }.get(scores.get("tier", "C"), "No Hire"),

        # 4D breakdown
        "score_breakdown":    score_breakdown,

        # Similarity evidence
        "top_matches":        top_matches,

        # Flags
        "red_flags":          scores.get("red_flags", []),
        "green_flags":        scores.get("green_flags", []),

        # Metadata
        "evaluated_at":       datetime.utcnow().isoformat() + "Z",
    }

    overall = final_report["overall_score"]
    tier    = final_report["tier"]
    label   = final_report["tier_label"]
    print(f"\n[report] ✓ Final report built for '{final_report['candidate_name']}'")
    print(f"[report]   Overall: {overall}/100 | Tier {tier} ({label})")

    return {**state, "final_report": final_report}