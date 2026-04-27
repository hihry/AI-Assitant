"""
graph.py
────────
LangGraph pipeline definition for the Resume Scoring System.

Graph topology:
    parse_resume → similarity_search → scorer → build_report → END

Usage:
    from graph import build_graph
    app = build_graph()
    result = app.invoke({
        "jd_text":   json.dumps(jd_data),
        "pdf_bytes": pdf_bytes,
    })
    report = result["final_report"]
"""

import sys
from pathlib import Path

from langgraph.graph import StateGraph, END

sys.path.insert(0, str(Path(__file__).parent))
from state import PipelineState
from modules.parse_resume   import parse_resume_node
from modules.similarity     import similarity_search_node
from modules.scorer         import scorer_node
from modules.build_report   import build_report_node


def build_graph() -> StateGraph:
    """
    Construct and compile the LangGraph pipeline.

    Returns a compiled graph that accepts PipelineState as input
    and returns PipelineState with final_report populated.
    """
    graph = StateGraph(PipelineState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("parse_resume",      parse_resume_node)
    graph.add_node("similarity_search", similarity_search_node)
    graph.add_node("scorer",            scorer_node)
    graph.add_node("build_report",      build_report_node)

    # ── Define edges (linear pipeline) ───────────────────────────────────────
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume",      "similarity_search")
    graph.add_edge("similarity_search", "scorer")
    graph.add_edge("scorer",            "build_report")
    graph.add_edge("build_report",      END)

    return graph.compile()


# ── Module-level compiled app (import this in main.py) ───────────────────────
app = build_graph()


# ── CLI smoke test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    from pathlib import Path

    pdf_path = Path("sample_data/resume_sample.pdf")
    jd_path  = Path("sample_data/jd_sample.json")

    if not pdf_path.exists():
        print(f"[graph] PDF not found: {pdf_path}")
        raise SystemExit(1)
    if not jd_path.exists():
        print(f"[graph] JD not found: {jd_path}")
        raise SystemExit(1)

    pdf_bytes = pdf_path.read_bytes()
    jd_data   = json.loads(jd_path.read_text())

    print("=" * 55)
    print("  Resume Scoring Pipeline — End-to-End Run")
    print("=" * 55)

    result = app.invoke({
        "jd_text":            json.dumps(jd_data),
        "pdf_bytes":          pdf_bytes,
        "resume_json":        None,
        "pinecone_matches":   None,
        "score_result":       None,
        "final_report":       None,
    })

    report = result["final_report"]

    print("\n" + "=" * 55)
    print("  FINAL REPORT")
    print("=" * 55)
    print(f"  Candidate : {report['candidate_name']}")
    print(f"  Experience: {report['experience_years']} year(s)")
    print(f"  Overall   : {report['overall_score']}/100")
    print(f"  Tier      : {report['tier']} — {report['tier_label']}")
    print()
    print("  Score Breakdown:")
    for dim in report["score_breakdown"]:
        bar = "█" * (dim["score"] // 5)
        print(f"    {dim['dimension']:<22} {dim['score']:>3}/100  {bar}")
    print()
    print("  Top Semantic Matches:")
    for m in report["top_matches"][:5]:
        print(f"    {m['cosine']:.2f}  '{m['resume_skill']}' → '{m['jd_requirement'][:50]}'")
    print()
    print("  Red Flags:")
    for f in report["red_flags"]:   print(f"    ✗ {f}")
    print("  Green Flags:")
    for f in report["green_flags"]: print(f"    ✓ {f}")
    print()
    print(json.dumps(report, indent=2))