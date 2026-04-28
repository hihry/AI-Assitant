# AI Resume Shortlisting & Scoring System
**Track:** AI / Backend · **Stack:** Python + LangGraph + Pinecone + Groq · **Scope:** Option A — Evaluation & Scoring Engine

---

## What This Does

An end-to-end pipeline that evaluates candidates by comparing resumes against a Job Description using **real vector similarity** (Pinecone) and **LLM reasoning** (Groq/Llama), orchestrated via **LangGraph**.

Every score comes with a human-readable *why* — built for the rubric criteria on Prompt Engineering / Explainability and Problem Solving.

---

## Prerequisites

- Python 3.10+
- Pinecone account (free tier is sufficient)
- Groq account (free tier is sufficient)
- A text-based PDF resume (image-only PDFs may fail extraction)

---

## Quickstart (2 Minutes)

```bash
# 1) Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Create .env from template and add keys
cp .env.example .env

# 4) Ingest sample JD once
python -m modules.ingest_jd --jd sample_data/jd_sample.json

# 5) Launch UI
streamlit run main.py
```

---

## Architecture

```
JD Ingestion (once per JD)
──────────────────────────────────────────────────────────
JD JSON → chunk by requirement → embed (sentence-transformers)
        → upsert to Pinecone [namespace: jd-requirements]

Resume Evaluation Pipeline (per candidate)
──────────────────────────────────────────────────────────
PDF Resume
    │
    ▼
[Node 1] parse_resume          PyPDF2 + Groq/Llama
    Extracts: name, skills[], projects[], experience_years, links{}
    │
    ▼
[Node 2] similarity_search     sentence-transformers + Pinecone
    Embeds each resume skill/project chunk locally
    Queries Pinecone → cosine match per chunk
    Key result: 'AWS Kinesis' → 'Apache Kafka requirement' = 0.91 cosine
    │
    ▼
[Node 3] scorer                Groq/Llama
    Computes 3 LLM scores + merges Pinecone similarity score:
      • Exact Score       (30%) — hard keyword overlap
      • Similarity Score  (35%) — Pinecone cosine vectors  ← real math
      • Achievement Score (20%) — quantified impact bullets
      • Ownership Score   (15%) — strong vs weak verb analysis
    Overall = weighted average
    │
    ▼
[Node 4] build_report          pure Python
    Assembles final scorecard with all reasoning + red/green flags
    │
    ▼
Streamlit UI renders everything
```

![Pipeline execution and control panel](Images/Screenshot%202026-04-27%20203847.png)

This view shows the end-to-end pipeline execution state from resume upload to final report assembly.
The left panel mirrors the operational flow: upload resume, provide JD, optionally seed Pinecone, then evaluate.
The status messages make node-level progress explicit for easier debugging and demos.

---

## 4D Scoring Model

| Dimension | Source | Weight | What it measures |
|-----------|--------|--------|-----------------|
| Exact Match | Groq/Llama | 30% | Hard skill keyword overlap |
| Semantic Similarity | Pinecone | **35%** | Tech equivalence (Kinesis ↔ Kafka) |
| Achievement | Groq/Llama | 20% | Quantified impact bullets |
| Ownership | Groq/Llama | 15% | Strong vs weak action verbs |

**Tier classification:** A ≥ 75 / B ≥ 50 / C < 50

![4D score cards in UI](Images/Screenshot%202026-04-27%20203926.png)

These score cards visualize the four weighted dimensions used in final ranking.
Each card surfaces both the raw score and its configured weight, reinforcing scoring transparency.
The compact layout helps recruiters scan candidate strength patterns quickly.

---

## Tech Stack (Free-Tier Friendly)

| Layer | Choice | Cost |
|-------|--------|------|
| Orchestration | LangGraph | free |
| Vector DB | Pinecone (serverless) | free tier |
| LLM | Groq — llama-3.3-70b-versatile | free tier |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | local, free |
| PDF parsing | PyPDF2 | free |
| UI | Streamlit | free |

---

## Project Structure

```
AI-Assitant/
├── main.py                        # Streamlit UI
├── graph.py                       # LangGraph pipeline (4 nodes)
├── state.py                       # PipelineState TypedDict
├── config.py                      # API/config constants + scoring weights
├── Architecture.md                # System design notes
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── .streamlit/
│   └── config.toml                # Streamlit runtime config
│
├── modules/
│   ├── ingest_jd.py               # JD → Pinecone (run once per JD)
│   ├── parse_resume.py            # Node 1: PDF → ResumeJSON
│   ├── similarity.py              # Node 2: Pinecone similarity search
│   ├── scorer.py                  # Node 3: LLM scoring
│   └── build_report.py            # Node 4: final report assembly
│
├── prompts/
│   ├── parse_resume.txt           # Resume parsing prompt
│   ├── score_candidate.txt        # Scoring prompt
│   └── generate_questions.txt     # Question generation prompt
│
└── sample_data/
    ├── jd_sample.json             # Sample JD
    └── resume_sample.pdf          # Sample resume
```

---

## Setup

### 1. Clone & install
```bash
git clone <repo>
cd AI-Assitant
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. Get free API keys
| Service | URL | Notes |
|---------|-----|-------|
| Groq | [console.groq.com](https://console.groq.com) | No credit card |
| Pinecone | [pinecone.io](https://pinecone.io) | Free serverless tier |

Create a Pinecone index:
- Name: `resume-shortlister`
- Dimension: `384`
- Metric: `cosine`
- Cloud: `aws` / Region: `us-east-1`

### 3. Configure
```bash
cp .env.example .env
# Edit .env and fill in your keys:
# GROQ_API_KEY=...
# PINECONE_API_KEY=...
```

### 4. Ingest the sample JD into Pinecone (once)
```bash
python -m modules.ingest_jd --jd sample_data/jd_sample.json
# Output chunk count varies by JD content.
```

### 5. Run the UI
```bash
streamlit run main.py
```

---

## Testing Each Module Independently

```bash
# Test PDF parsing (needs GROQ_API_KEY)
python -m modules.parse_resume sample_data/resume_sample.pdf

# Test similarity search (needs PINECONE_API_KEY + JD ingested)
python -m modules.similarity

# Test scorer (needs GROQ_API_KEY)
python -m modules.scorer

# Test full pipeline end-to-end
python graph.py
```

---

## Sample Output

```
Candidate : Arjun Mehta
Experience: 5 year(s)
Overall   : 83/100
Tier      : A — Strong Hire

Score Breakdown:
  Exact Match            78/100  ███████████████░░░░░
  Semantic Similarity    84/100  ████████████████░░░░  ← Pinecone
  Achievement            85/100  █████████████████░░░
  Ownership              90/100  ██████████████████░░

Top Semantic Matches:
  0.97  'Python'      → 'Strong proficiency in Python or Go'
  0.95  'PostgreSQL'  → 'Proficiency with PostgreSQL and Redis'
  0.93  'Terraform'   → 'Experience with Terraform or similar IaC tools'
  0.91  'AWS Kinesis' → 'Experience with Apache Kafka or similar message queues'
  0.88  'Docker'      → 'Experience with Docker and Kubernetes'

Red Flags:
  ✗ No explicit Kubernetes experience despite it being required
  ✗ No GCP mentioned

Green Flags:
  ✓ AWS Kinesis maps to Kafka requirement (cosine 0.91)
  ✓ All 4 projects have quantified impact metrics
  ✓ Strong ownership verbs throughout (built, led, architected, owned)
```

![Reasoning, semantic evidence, and flags](Images/Screenshot%202026-04-27%20203941.png)

This section demonstrates explainability in practice: per-dimension reasoning, semantic match evidence, and risk signals.
The cosine evidence table grounds similarity scoring in concrete resume-to-JD mappings.
Red and green flags translate model output into actionable hiring guidance.

---

## Key Design Decisions

### Why Pinecone for similarity (not LLM)?
Asking an LLM to compute "how similar is Kinesis to Kafka?" produces inconsistent results. Pinecone returns a deterministic cosine score (0.91) backed by real vector math — reproducible, explainable, and fast.

### Why separate Exact from Similarity?
Exact score counts verbatim matches ("Python" = "Python"). Similarity score captures tech equivalence ("AWS Kinesis" ≈ "Apache Kafka"). Keeping them separate makes the scoring transparent — a candidate can score high on Similarity without having exact keyword matches.

### Why temperature=0.0 on all LLM calls?
Scoring must be deterministic. The same resume evaluated twice should return the same scores. Temperature 0.0 eliminates randomness from all Groq calls.

### Why strict validation and fallback defaults across nodes?
LLMs can omit fields or return malformed JSON despite strict prompts. The pipeline uses validation/defaulting patterns in parser and scorer paths so downstream nodes do not fail on missing keys.

---

## Known Issues / Notes

- If you run module files as script paths (for example, python modules/file.py), imports may fail in some environments. Prefer module-style commands: python -m modules.<name>.
- Streamlit + torch package watchers can throw runtime errors in some Windows setups. This repo includes .streamlit/config.toml with fileWatcherType set to none.
- If you hit Unicode decode issues on Windows while reading prompt/sample files, ensure UTF-8 file reads are used.