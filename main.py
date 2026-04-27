# """Streamlit UI entrypoint for the resume shortlister app."""


# def main() -> None:
#     """Run the Streamlit application."""
#     raise NotImplementedError("Implement Streamlit UI in main.py")


# if __name__ == "__main__":
#     main()

import streamlit as st
import pandas as pd
import json
from pathlib import Path

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(
    page_title="AI Resume Shortlisting Report",
    page_icon="📄",
    layout="wide"
)

# ==========================================
# 2. Mock Data (From your context)
# ==========================================
mock_report = {
    "candidate_name": "Arjun Mehta",
    "candidate_email": "arjun.mehta@email.com",
    "experience_years": 5,
    "skills": ["Python", "Go", "FastAPI", "PostgreSQL", "AWS Kinesis", "Docker", "Terraform"],
    "github": "github.com/arjunmehta",
    "linkedin": None,
    "overall_score": 83,
    "tier": "A",
    "tier_label": "Strong Hire",
    "score_breakdown": [
        {"dimension": "Exact Match", "score": 78, "weight": "30%", "reasoning": "Matched 7/10 skills. Missing: Kubernetes, GCP."},
        {"dimension": "Semantic Similarity", "score": 84, "weight": "35%", "reasoning": "AWS Kinesis → Kafka (0.91), PostgreSQL → relational DB (0.95)"},
        {"dimension": "Achievement", "score": 85, "weight": "20%", "reasoning": "4 quantified bullets: 2M events/day, 60% faster, 45% DB reduction, 500K DAU."},
        {"dimension": "Ownership", "score": 90, "weight": "15%", "reasoning": "4/4 projects: built, led, architected, owned."},
    ],
    "top_matches": [
        {"resume_skill": "AWS Kinesis", "jd_requirement": "Experience with Apache Kafka or similar...", "cosine": 0.91},
        {"resume_skill": "PostgreSQL", "jd_requirement": "Proficiency with PostgreSQL and Redis", "cosine": 0.95},
        {"resume_skill": "Docker", "jd_requirement": "Experience with Docker and Kubernetes", "cosine": 0.88},
        {"resume_skill": "Terraform", "jd_requirement": "Experience with Terraform or similar IaC tools", "cosine": 0.93},
        {"resume_skill": "Python", "jd_requirement": "Strong proficiency in Python or Go", "cosine": 0.97},
    ],
    "red_flags": ["No explicit Kubernetes experience", "No GCP mentioned"],
    "green_flags": ["AWS Kinesis maps to Kafka requirement", "All 4 projects quantified", "Strong ownership verbs throughout"],
    "evaluated_at": "2025-04-27T10:00:00Z",
}


def run_pipeline_and_get_report(pdf_bytes: bytes, jd_data: dict) -> dict:
    from graph import app

    result = app.invoke(
        {
            "jd_text": json.dumps(jd_data),
            "pdf_bytes": pdf_bytes,
            "resume_json": None,
            "pinecone_matches": None,
            "score_result": None,
            "final_report": None,
        }
    )
    return result["final_report"]


def load_default_jd() -> dict:
    jd_path = Path("sample_data/jd_sample.json")
    if jd_path.exists():
        return json.loads(jd_path.read_text(encoding="utf-8"))
    return {
        "title": "Job Description",
        "requirements": [],
        "responsibilities": [],
    }

# ==========================================
# 3. Helper Functions (Adapted for Web)
# ==========================================
def score_color(score):
    if score >= 75: return "#a6e3a1"  # Green
    if score >= 50: return "#f9e2af"  # Yellow
    return "#f38ba8"                  # Red

def tier_style(tier):
    styles = {
        "A": "background:#1b2d1b; color:#a6e3a1; border:2px solid #a6e3a1;",
        "B": "background:#2d2b1b; color:#f9e2af; border:2px solid #f9e2af;",
        "C": "background:#2d1b1b; color:#f38ba8; border:2px solid #f38ba8;",
    }
    return styles.get(tier, "")

def render_progress_bar(score, label=""):
    """Creates a custom HTML progress bar to strictly use your hex colors."""
    color = score_color(score)
    html = f"""
    <div style="margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <strong>{label}</strong>
            <span style="color: {color}; font-weight: bold;">{score}/100</span>
        </div>
        <div style="width: 100%; background-color: #2b2b2b; border-radius: 8px; overflow: hidden; height: 12px;">
            <div style="width: {score}%; background-color: {color}; height: 100%;"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ==========================================
# 4. Main UI Layout
# ==========================================

with st.expander("Run Real Evaluation", expanded=False):
    uploaded_pdf = st.file_uploader("Upload Resume PDF", type=["pdf"])
    default_jd_data = load_default_jd()
    jd_text_input = st.text_area(
        "JD JSON",
        value=json.dumps(default_jd_data, indent=2),
        height=240,
    )

    if st.button("Run Pipeline", type="primary"):
        if not uploaded_pdf:
            st.error("Please upload a resume PDF first.")
        else:
            try:
                jd_data = json.loads(jd_text_input)
                with st.spinner("Running parse -> similarity -> scorer -> report..."):
                    report = run_pipeline_and_get_report(uploaded_pdf.read(), jd_data)
                st.session_state["report"] = report
                st.success("Evaluation complete.")
            except json.JSONDecodeError as exc:
                st.error(f"JD JSON is invalid: {exc}")
            except Exception as exc:
                st.error(f"Pipeline failed: {exc}")

mock_report = st.session_state.get("report", mock_report)

# --- Header Section ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title(f"📄 {mock_report['candidate_name']}")
    st.markdown(f"**Experience:** {mock_report['experience_years']} Years | **Email:** {mock_report['candidate_email']} | **GitHub:** {mock_report['github']}")

with col2:
    # Render Tier Badge and Overall Score
    badge_css = tier_style(mock_report['tier'])
    badge_html = f"""
    <div style="text-align: right;">
        <h2 style="margin-bottom: 5px;">Overall: {mock_report['overall_score']}/100</h2>
        <span style="{badge_css} padding: 6px 16px; border-radius: 20px; font-size: 16px; font-weight: 600; display: inline-block;">
            Tier {mock_report['tier']} — {mock_report['tier_label']}
        </span>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)

st.divider()

# --- Main Content Grid ---
left_col, right_col = st.columns([1, 1])

# --- Left Column: Scoring & Flags ---
with left_col:
    st.subheader("📊 4D Score Breakdown")
    for dim in mock_report["score_breakdown"]:
        render_progress_bar(dim["score"], dim["dimension"])
        st.caption(f"_{dim['reasoning']}_")
        st.write("") # Spacer

    st.subheader("🚩 Evaluation Flags")
    flag_col1, flag_col2 = st.columns(2)
    with flag_col1:
        st.markdown("**Green Flags**")
        for flag in mock_report["green_flags"]:
            st.success(flag, icon="✅")
    with flag_col2:
        st.markdown("**Red Flags**")
        for flag in mock_report["red_flags"]:
            st.error(flag, icon="❌")

# --- Right Column: Matches & Skills ---
with right_col:
    st.subheader("🔍 Semantic Matches")
    # Convert top matches to a clean pandas dataframe for native rendering
    df_matches = pd.DataFrame(mock_report["top_matches"])
    df_matches["Score"] = df_matches["cosine"].apply(lambda x: f"{x:.2f}")
    df_matches = df_matches[["Score", "resume_skill", "jd_requirement"]]
    df_matches.columns = ["Score", "Resume Skill", "JD Requirement (Matched against)"]
    
    st.dataframe(
        df_matches, 
        use_container_width=True, 
        hide_index=True
    )

    st.subheader("🛠️ Extracted Skills")
    # Render skills as styled pills/tags
    skills_html = ""
    for skill in mock_report["skills"]:
        skills_html += f'<span style="background-color: #3b3b3b; padding: 4px 10px; border-radius: 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 14px;">{skill}</span>'
    st.markdown(skills_html, unsafe_allow_html=True)

st.caption(f"Evaluated at: {mock_report['evaluated_at']}")