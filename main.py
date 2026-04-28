# # """Streamlit UI entrypoint for the resume shortlister app."""


# # def main() -> None:
# #     """Run the Streamlit application."""
# #     raise NotImplementedError("Implement Streamlit UI in main.py")


# # if __name__ == "__main__":
# #     main()

# import streamlit as st
# import pandas as pd
# import json
# from pathlib import Path

# # ==========================================
# # 1. Page Configuration
# # ==========================================
# st.set_page_config(
#     page_title="AI Resume Shortlisting Report",
#     page_icon="📄",
#     layout="wide"
# )

# # ==========================================
# # 2. Mock Data (From your context)
# # ==========================================
# mock_report = {
#     "candidate_name": "Arjun Mehta",
#     "candidate_email": "arjun.mehta@email.com",
#     "experience_years": 5,
#     "skills": ["Python", "Go", "FastAPI", "PostgreSQL", "AWS Kinesis", "Docker", "Terraform"],
#     "github": "github.com/arjunmehta",
#     "linkedin": None,
#     "overall_score": 83,
#     "tier": "A",
#     "tier_label": "Strong Hire",
#     "score_breakdown": [
#         {"dimension": "Exact Match", "score": 78, "weight": "30%", "reasoning": "Matched 7/10 skills. Missing: Kubernetes, GCP."},
#         {"dimension": "Semantic Similarity", "score": 84, "weight": "35%", "reasoning": "AWS Kinesis → Kafka (0.91), PostgreSQL → relational DB (0.95)"},
#         {"dimension": "Achievement", "score": 85, "weight": "20%", "reasoning": "4 quantified bullets: 2M events/day, 60% faster, 45% DB reduction, 500K DAU."},
#         {"dimension": "Ownership", "score": 90, "weight": "15%", "reasoning": "4/4 projects: built, led, architected, owned."},
#     ],
#     "top_matches": [
#         {"resume_skill": "AWS Kinesis", "jd_requirement": "Experience with Apache Kafka or similar...", "cosine": 0.91},
#         {"resume_skill": "PostgreSQL", "jd_requirement": "Proficiency with PostgreSQL and Redis", "cosine": 0.95},
#         {"resume_skill": "Docker", "jd_requirement": "Experience with Docker and Kubernetes", "cosine": 0.88},
#         {"resume_skill": "Terraform", "jd_requirement": "Experience with Terraform or similar IaC tools", "cosine": 0.93},
#         {"resume_skill": "Python", "jd_requirement": "Strong proficiency in Python or Go", "cosine": 0.97},
#     ],
#     "red_flags": ["No explicit Kubernetes experience", "No GCP mentioned"],
#     "green_flags": ["AWS Kinesis maps to Kafka requirement", "All 4 projects quantified", "Strong ownership verbs throughout"],
#     "evaluated_at": "2025-04-27T10:00:00Z",
# }


# def run_pipeline_and_get_report(pdf_bytes: bytes, jd_data: dict) -> dict:
#     from graph import app

#     result = app.invoke(
#         {
#             "jd_text": json.dumps(jd_data),
#             "pdf_bytes": pdf_bytes,
#             "resume_json": None,
#             "pinecone_matches": None,
#             "score_result": None,
#             "final_report": None,
#         }
#     )
#     return result["final_report"]


# def load_default_jd() -> dict:
#     jd_path = Path("sample_data/jd_sample.json")
#     if jd_path.exists():
#         return json.loads(jd_path.read_text(encoding="utf-8"))
#     return {
#         "title": "Job Description",
#         "requirements": [],
#         "responsibilities": [],
#     }

# # ==========================================
# # 3. Helper Functions (Adapted for Web)
# # ==========================================
# def score_color(score):
#     if score >= 75: return "#a6e3a1"  # Green
#     if score >= 50: return "#f9e2af"  # Yellow
#     return "#f38ba8"                  # Red

# def tier_style(tier):
#     styles = {
#         "A": "background:#1b2d1b; color:#a6e3a1; border:2px solid #a6e3a1;",
#         "B": "background:#2d2b1b; color:#f9e2af; border:2px solid #f9e2af;",
#         "C": "background:#2d1b1b; color:#f38ba8; border:2px solid #f38ba8;",
#     }
#     return styles.get(tier, "")

# def render_progress_bar(score, label=""):
#     """Creates a custom HTML progress bar to strictly use your hex colors."""
#     color = score_color(score)
#     html = f"""
#     <div style="margin-bottom: 10px;">
#         <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
#             <strong>{label}</strong>
#             <span style="color: {color}; font-weight: bold;">{score}/100</span>
#         </div>
#         <div style="width: 100%; background-color: #2b2b2b; border-radius: 8px; overflow: hidden; height: 12px;">
#             <div style="width: {score}%; background-color: {color}; height: 100%;"></div>
#         </div>
#     </div>
#     """
#     st.markdown(html, unsafe_allow_html=True)

# # ==========================================
# # 4. Main UI Layout
# # ==========================================

# with st.expander("Run Real Evaluation", expanded=False):
#     uploaded_pdf = st.file_uploader("Upload Resume PDF", type=["pdf"])
#     default_jd_data = load_default_jd()
#     jd_text_input = st.text_area(
#         "JD JSON",
#         value=json.dumps(default_jd_data, indent=2),
#         height=240,
#     )

#     if st.button("Run Pipeline", type="primary"):
#         if not uploaded_pdf:
#             st.error("Please upload a resume PDF first.")
#         else:
#             try:
#                 jd_data = json.loads(jd_text_input)
#                 with st.spinner("Running parse -> similarity -> scorer -> report..."):
#                     report = run_pipeline_and_get_report(uploaded_pdf.read(), jd_data)
#                 st.session_state["report"] = report
#                 st.success("Evaluation complete.")
#             except json.JSONDecodeError as exc:
#                 st.error(f"JD JSON is invalid: {exc}")
#             except Exception as exc:
#                 st.error(f"Pipeline failed: {exc}")

# mock_report = st.session_state.get("report", mock_report)

# # --- Header Section ---
# col1, col2 = st.columns([3, 1])
# with col1:
#     st.title(f"📄 {mock_report['candidate_name']}")
#     st.markdown(f"**Experience:** {mock_report['experience_years']} Years | **Email:** {mock_report['candidate_email']} | **GitHub:** {mock_report['github']}")

# with col2:
#     # Render Tier Badge and Overall Score
#     badge_css = tier_style(mock_report['tier'])
#     badge_html = f"""
#     <div style="text-align: right;">
#         <h2 style="margin-bottom: 5px;">Overall: {mock_report['overall_score']}/100</h2>
#         <span style="{badge_css} padding: 6px 16px; border-radius: 20px; font-size: 16px; font-weight: 600; display: inline-block;">
#             Tier {mock_report['tier']} — {mock_report['tier_label']}
#         </span>
#     </div>
#     """
#     st.markdown(badge_html, unsafe_allow_html=True)

# st.divider()

# # --- Main Content Grid ---
# left_col, right_col = st.columns([1, 1])

# # --- Left Column: Scoring & Flags ---
# with left_col:
#     st.subheader("📊 4D Score Breakdown")
#     for dim in mock_report["score_breakdown"]:
#         render_progress_bar(dim["score"], dim["dimension"])
#         st.caption(f"_{dim['reasoning']}_")
#         st.write("") # Spacer

#     st.subheader("🚩 Evaluation Flags")
#     flag_col1, flag_col2 = st.columns(2)
#     with flag_col1:
#         st.markdown("**Green Flags**")
#         for flag in mock_report["green_flags"]:
#             st.success(flag, icon="✅")
#     with flag_col2:
#         st.markdown("**Red Flags**")
#         for flag in mock_report["red_flags"]:
#             st.error(flag, icon="❌")

# # --- Right Column: Matches & Skills ---
# with right_col:
#     st.subheader("🔍 Semantic Matches")
#     # Convert top matches to a clean pandas dataframe for native rendering
#     df_matches = pd.DataFrame(mock_report["top_matches"])
#     df_matches["Score"] = df_matches["cosine"].apply(lambda x: f"{x:.2f}")
#     df_matches = df_matches[["Score", "resume_skill", "jd_requirement"]]
#     df_matches.columns = ["Score", "Resume Skill", "JD Requirement (Matched against)"]
    
#     st.dataframe(
#         df_matches, 
#         use_container_width=True, 
#         hide_index=True
#     )

#     st.subheader("🛠️ Extracted Skills")
#     # Render skills as styled pills/tags
#     skills_html = ""
#     for skill in mock_report["skills"]:
#         skills_html += f'<span style="background-color: #3b3b3b; padding: 4px 10px; border-radius: 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 14px;">{skill}</span>'
#     st.markdown(skills_html, unsafe_allow_html=True)

# st.caption(f"Evaluated at: {mock_report['evaluated_at']}")

"""
main.py
───────
Streamlit UI for the AI Resume Shortlisting System.

Run:
    streamlit run main.py
"""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="AI Resume Shortlister",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Score cards */
    .score-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border: 1px solid #313244;
    }
    .score-number {
        font-size: 2.8rem;
        font-weight: 700;
        line-height: 1;
    }
    .score-label {
        font-size: 0.85rem;
        color: #a6adc8;
        margin-top: 6px;
    }
    .score-weight {
        font-size: 0.75rem;
        color: #6c7086;
        margin-top: 2px;
    }

    /* Tier badge */
    .tier-badge {
        display: inline-block;
        padding: 8px 28px;
        border-radius: 50px;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    /* Flag pills */
    .flag-red   { background:#2d1b1b; border:1px solid #f38ba8;
                  border-radius:8px; padding:6px 12px; margin:4px 0;
                  color:#f38ba8; font-size:0.875rem; }
    .flag-green { background:#1b2d1b; border:1px solid #a6e3a1;
                  border-radius:8px; padding:6px 12px; margin:4px 0;
                  color:#a6e3a1; font-size:0.875rem; }

    /* Reasoning box */
    .reasoning-box {
        background:#181825;
        border-left: 3px solid #89b4fa;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        font-size:0.875rem;
        color:#cdd6f4;
        white-space: pre-wrap;
        line-height: 1.6;
    }

    /* Match row */
    .match-row {
        display:flex;
        align-items:center;
        gap:12px;
        padding:8px 0;
        border-bottom:1px solid #313244;
        font-size:0.875rem;
    }

    /* Skill pills */
    .skill-pill {
        display:inline-block;
        background:#313244;
        border-radius:6px;
        padding:3px 10px;
        margin:3px;
        font-size:0.8rem;
        color:#cdd6f4;
    }

    /* Section dividers */
    hr { border-color:#313244; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(score: int) -> str:
    if score >= 75: return "#a6e3a1"   # green
    if score >= 50: return "#f9e2af"   # yellow
    return "#f38ba8"                   # red

def tier_style(tier: str) -> str:
    styles = {
        "A": "background:#1b2d1b; color:#a6e3a1; border:2px solid #a6e3a1;",
        "B": "background:#2d2b1b; color:#f9e2af; border:2px solid #f9e2af;",
        "C": "background:#2d1b1b; color:#f38ba8; border:2px solid #f38ba8;",
    }
    return styles.get(tier, "")

def cosine_bar(cosine: float) -> str:
    filled = int(cosine * 20)
    return "█" * filled + "░" * (20 - filled)

def render_score_card(label: str, score: int, weight: str, source: str = ""):
    color = score_color(score)
    src   = f'<div class="score-weight">{source}</div>' if source else ""
    st.markdown(f"""
    <div class="score-card">
        <div class="score-number" style="color:{color}">{score}</div>
        <div style="font-size:0.7rem;color:#6c7086;">/100</div>
        <div class="score-label">{label}</div>
        <div class="score-weight">weight: {weight}</div>
        {src}
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar — Inputs ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Resume Shortlister")
    st.caption("Powered by LangGraph + Pinecone + Groq")
    st.divider()

    st.subheader("① Upload Resume")
    uploaded_pdf = st.file_uploader(
        "Drop a PDF resume here",
        type=["pdf"],
        help="Text-based PDFs only (not scanned images)",
    )

    st.subheader("② Paste Job Description")
    jd_input_mode = st.radio(
        "JD input format",
        ["Use sample JD", "Paste JSON", "Paste plain text"],
        index=0,
    )

    jd_data = None

    if jd_input_mode == "Use sample JD":
        sample_path = Path("sample_data/jd_sample.json")
        if sample_path.exists():
            jd_data = json.loads(sample_path.read_text())
            st.success(f"Loaded: **{jd_data.get('title')}** @ {jd_data.get('company')}")
        else:
            st.error("sample_data/jd_sample.json not found.")

    elif jd_input_mode == "Paste JSON":
        raw_json = st.text_area("Paste JD JSON", height=200,
                                placeholder='{"id":"jd-001","requirements":[...],...}')
        if raw_json.strip():
            try:
                jd_data = json.loads(raw_json)
                st.success("✓ Valid JSON")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")

    else:  # Plain text
        raw_text = st.text_area("Paste JD text", height=200,
                                placeholder="5+ years Python experience\nKafka or similar...")
        if raw_text.strip():
            lines   = [l.strip("•- ").strip() for l in raw_text.splitlines() if l.strip()]
            jd_data = {"id": "jd-manual", "requirements": lines, "responsibilities": []}
            st.success(f"✓ Parsed {len(lines)} requirement line(s)")

    st.divider()

    # Ingest JD button (seeds Pinecone — run once per JD)
    st.subheader("③ Seed Pinecone")
    st.caption("Run once per JD to build the vector index.")
    if st.button("⬆ Ingest JD → Pinecone", use_container_width=True, type="secondary"):
        if jd_data:
            with st.spinner("Ingesting JD into Pinecone..."):
                try:
                    from modules.ingest_jd import ingest_jd
                    summary = ingest_jd(jd_data)
                    st.success(f"✓ {summary['chunks_ingested']} chunks indexed")
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")
        else:
            st.warning("Load a JD first.")

    st.divider()

    # Evaluate button
    evaluate = st.button(
        "🚀 Evaluate Resume",
        use_container_width=True,
        type="primary",
        disabled=(uploaded_pdf is None or jd_data is None),
    )

    if uploaded_pdf is None:
        st.caption("⬆ Upload a PDF resume to continue.")
    if jd_data is None:
        st.caption("⬆ Load a JD to continue.")


# ── Main panel ────────────────────────────────────────────────────────────────
st.title("AI Resume Shortlisting & Scoring")
st.caption("Option A — Evaluation & Scoring Engine | Stack: LangGraph · Pinecone · Groq Llama")

if not evaluate:
    # Landing state
    st.info("Upload a resume PDF and load a JD in the sidebar, then click **Evaluate Resume**.")

    with st.expander("How it works", expanded=True):
        st.markdown("""
        **Pipeline:**
        ```
        PDF Resume + Job Description
               │
               ▼
        [Node 1] parse_resume       PDF → structured JSON (Groq/Llama)
               │
               ▼
        [Node 2] similarity_search  embed resume chunks → query Pinecone
               │                   cosine match: 'AWS Kinesis' ↔ 'Apache Kafka' = 0.91
               ▼
        [Node 3] scorer             Exact + Achievement + Ownership (Groq/Llama)
               │
               ▼
        [Node 4] build_report       assemble final 4D scorecard + reasoning
        ```

        **4 Scoring Dimensions:**
        | Dimension | Source | Weight |
        |-----------|--------|--------|
        | Exact Match | Llama keyword analysis | 30% |
        | Semantic Similarity | Pinecone cosine vectors | 35% |
        | Achievement | Llama impact detection | 20% |
        | Ownership | Llama verb analysis | 15% |
        """)
    st.stop()


# ── Run pipeline ──────────────────────────────────────────────────────────────
pdf_bytes = uploaded_pdf.read()

with st.status("Running evaluation pipeline...", expanded=True) as status:
    try:
        from graph import app

        st.write("📄 Node 1 — Parsing resume with Groq/Llama...")
        st.write("🔍 Node 2 — Querying Pinecone for semantic matches...")
        st.write("🧮 Node 3 — Computing 4D scores...")
        st.write("📊 Node 4 — Assembling final report...")

        result = app.invoke({
            "jd_text":          json.dumps(jd_data),
            "pdf_bytes":        pdf_bytes,
            "resume_json":      None,
            "pinecone_matches": None,
            "score_result":     None,
            "final_report":     None,
        })

        report = result["final_report"]
        status.update(label="✅ Evaluation complete", state="complete")

    except Exception as e:
        status.update(label="❌ Pipeline failed", state="error")
        st.error(f"**Error:** {e}")
        st.exception(e)
        st.stop()


# ── Report rendering ──────────────────────────────────────────────────────────
st.divider()

# ── Candidate header ──────────────────────────────────────────────────────────
col_name, col_verdict = st.columns([2, 1])

with col_name:
    st.subheader(f"📋 {report['candidate_name']}")
    if report.get("candidate_email"):
        st.caption(f"✉ {report['candidate_email']}")
    meta_parts = [f"**{report['experience_years']} yr(s)** experience"]
    if report.get("github"):
        meta_parts.append(f"[GitHub]({report['github']})")
    if report.get("linkedin"):
        meta_parts.append(f"[LinkedIn]({report['linkedin']})")
    st.markdown("  ·  ".join(meta_parts))

with col_verdict:
    tier      = report["tier"]
    label     = report["tier_label"]
    overall   = report["overall_score"]
    col_score, col_tier = st.columns(2)
    with col_score:
        st.metric("Overall Score", f"{overall}/100")
    with col_tier:
        st.markdown(
            f'<div class="tier-badge" style="{tier_style(tier)}">Tier {tier}</div>',
            unsafe_allow_html=True,
        )
        st.caption(label)

st.divider()

# ── 4D Score breakdown ────────────────────────────────────────────────────────
st.subheader("4D Score Breakdown")
breakdown = report["score_breakdown"]
cols = st.columns(4)

labels_meta = [
    ("Exact Match",          "30%", ""),
    ("Semantic Similarity",  "35%", "via Pinecone"),
    ("Achievement",          "20%", ""),
    ("Ownership",            "15%", ""),
]
for col, dim, (_, weight, source) in zip(cols, breakdown, labels_meta):
    with col:
        render_score_card(dim["dimension"], dim["score"], weight, source)
        st.progress(dim["score"] / 100)

st.divider()

# ── Reasoning per dimension ───────────────────────────────────────────────────
st.subheader("Score Reasoning")
tabs = st.tabs(["📌 Exact", "🔍 Similarity", "🏆 Achievement", "💪 Ownership"])

for tab, dim in zip(tabs, breakdown):
    with tab:
        st.markdown(
            f'<div class="reasoning-box">{dim["reasoning"]}</div>',
            unsafe_allow_html=True,
        )

st.divider()

# ── Semantic similarity matches table ─────────────────────────────────────────
st.subheader("Semantic Similarity Evidence")
st.caption("Pinecone vector matches — how resume skills map to JD requirements")

top_matches = report.get("top_matches", [])
if top_matches:
    match_rows = []
    for m in top_matches:
        cosine = m["cosine"]
        bar    = cosine_bar(cosine)
        color  = score_color(int(cosine * 100))
        match_rows.append({
            "Resume Skill":      m["resume_skill"],
            "JD Requirement":    m["jd_requirement"][:70] + ("…" if len(m["jd_requirement"]) > 70 else ""),
            "Section":           m["section"].replace("_", " ").title(),
            "Cosine":            f"{cosine:.3f}",
        })

    st.dataframe(
        match_rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cosine": st.column_config.ProgressColumn(
                "Cosine Score",
                min_value=0,
                max_value=1,
                format="%.3f",
            )
        },
    )
else:
    st.warning("No Pinecone matches found — ensure JD is ingested first.")

st.divider()

# ── Red / Green flags ─────────────────────────────────────────────────────────
col_red, col_green = st.columns(2)

with col_red:
    st.subheader("🚩 Red Flags")
    flags = report.get("red_flags", [])
    if flags:
        for f in flags:
            st.markdown(f'<div class="flag-red">✗ {f}</div>', unsafe_allow_html=True)
    else:
        st.success("No red flags detected.")

with col_green:
    st.subheader("✅ Green Flags")
    flags = report.get("green_flags", [])
    if flags:
        for f in flags:
            st.markdown(f'<div class="flag-green">✓ {f}</div>', unsafe_allow_html=True)
    else:
        st.info("No green flags detected.")

st.divider()

# ── Skills ────────────────────────────────────────────────────────────────────
st.subheader("Detected Skills")
skills_html = "".join(
    f'<span class="skill-pill">{s}</span>'
    for s in report.get("skills", [])
)
st.markdown(skills_html, unsafe_allow_html=True)

st.divider()

# ── Raw JSON export ───────────────────────────────────────────────────────────
with st.expander("📥 Export raw report JSON"):
    st.json(report)
    st.download_button(
        label="Download report.json",
        data=json.dumps(report, indent=2),
        file_name=f"report_{report['candidate_name'].replace(' ', '_').lower()}.json",
        mime="application/json",
    )