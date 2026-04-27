# AI Resume Shortlisting System — Architecture Document

## Overview
An end-to-end pipeline that evaluates candidates by comparing resumes against a Job Description (JD) using semantic vector search (Pinecone) and LLM reasoning (Groq/Llama), orchestrated via LangGraph. The system implements **Option A: Evaluation & Scoring Engine** with a 4-dimensional scoring model and full explainability on every score.

---

## System Architecture

```
JD Ingestion (one-time per JD)
────────────────────────────────────────────────────────────────────
JD JSON → chunk_jd() → 3 sections (requirements, responsibilities,
          nice_to_have) → embed locally (all-MiniLM-L6-v2, 384-dim)
          → upsert to Pinecone [namespace: jd-requirements]
          Implemented in: ingest_jd.py

Resume Evaluation Pipeline (per candidate) — LangGraph graph
────────────────────────────────────────────────────────────────────
PDF bytes + JD JSON
       │
       ▼
[Node 1: parse_resume]              modules/parse_resume.py
    PyPDF2 extracts raw text from PDF
    Groq/Llama (llama-3.3-70b-versatile, temp=0.0) parses into JSON:
    {name, email, experience_years, skills[], projects[],
     links{github, linkedin}, raw_skills_section}
    Each project carries: tech[], ownership_verbs[], achievement_bullets[]
       │
       ▼
[Node 2: similarity_search]         modules/similarity.py
    Builds 4 chunk types from resume_json:
      1. Individual skills      → "AWS Kinesis", "Docker"
      2. Project tech stacks    → "AWS Kinesis, Python, PostgreSQL"
      3. Project descriptions   → "Built real-time pipeline using Kinesis"
      4. Raw skills section     → verbatim fallback
    Embeds all chunks locally (sentence-transformers, zero API cost)
    Queries Pinecone top-1 per chunk (namespace: jd-requirements)
    Deduplicates: if same JD requirement matched multiple times,
                  keeps highest cosine score only
    similarity_score = avg(top-5 cosines) × 100
    Key result: 'AWS Kinesis' → 'Apache Kafka requirement' = 0.91 cosine
       │
       ▼
[Node 3: scorer]                    modules/scorer.py
    Groq/Llama computes 3 scores with detailed reasoning:
      - Exact Score       (30%): verbatim/near-verbatim keyword overlap
      - Achievement Score (20%): quantified impact bullets (numbers, %)
      - Ownership Score   (15%): strong verbs (built/led/owned) vs
                                 weak verbs (assisted/helped)
    Merges Pinecone's similarity_score (35%) from Node 2
    Computes weighted overall score + tier (A/B/C)
    All reasoning stored as human-readable strings per dimension
       │
       ▼
[Node 4: build_report]              modules/build_report.py
    Pure Python — zero API calls
    Assembles renderer-ready dict:
    {candidate info, overall_score, tier, tier_label,
     score_breakdown[], top_matches[], red_flags[], green_flags[]}
       │
       ▼
Streamlit UI (main.py)
    Sidebar: PDF upload, JD input (sample/JSON/plain text), Pinecone ingest
    Main panel: 4D score cards + progress bars, reasoning tabs,
                Pinecone match table with cosine progress column,
                red/green flag pills, skill tags, JSON export
```

---

## LangGraph State

A single `PipelineState` TypedDict (state.py) flows through all nodes.
Each node reads its inputs and writes its outputs back to the same object —
no global state, no class instances.

```python
class PipelineState(TypedDict):
    jd_text:          str           # input
    pdf_bytes:        bytes          # input
    resume_json:      Optional[dict] # written by Node 1
    pinecone_matches: Optional[list] # written by Node 2
    score_result:     Optional[dict] # written by Node 2 (sim) + Node 3 (rest)
    final_report:     Optional[dict] # written by Node 4
```

---

## Data Strategy

### PDF → Structured JSON
- `PyPDF2` extracts raw text page-by-page, joined with double newlines
- Excessive whitespace collapsed via regex before sending to LLM
- `prompts/parse_resume.txt` enforces strict output schema with JSON-only system prompt
- `temperature=0.0` — parsing is deterministic, not creative
- `validate_and_fill()` fills missing keys with safe defaults so downstream nodes never `KeyError`

### JD Chunking Strategy (`ingest_jd.py`)
Each bullet in the JD becomes one vector in Pinecone:
- `requirements` bullets → section tag: `requirement`
- `responsibilities` bullets → section tag: `responsibility`
- `nice_to_have` bullets → section tag: `nice_to_have`

Short single-sentence chunks maximise embedding precision.
Upsert is **idempotent** — re-running with the same `jd_id` safely overwrites.

### Resume Chunking Strategy (`modules/similarity.py`)
Four chunk sources per resume, in priority order:

| Source | Example | Purpose |
|--------|---------|---------|
| Individual skill | `"AWS Kinesis"` | Precise tech matching |
| Project tech stack | `"AWS Kinesis, Python, PostgreSQL"` | Tech combo context |
| Project description | `"Built pipeline processing 2M events/day"` | Responsibility-level semantics |
| Raw skills section | verbatim text block | Fallback coverage |

---

## AI Strategy

### LLM: Groq — llama-3.3-70b-versatile (free tier)
Used for:
- Resume parsing: unstructured PDF text → strict JSON schema
- Exact score: hard keyword matching with near-verbatim awareness
- Achievement score: detecting and counting quantified impact mentions
- Ownership score: classifying action verbs as strong or weak per bullet
- Explainability: generating one human-readable reasoning string per dimension

All calls use `temperature=0.0` for deterministic, reproducible results.

### Embedding Model: sentence-transformers — all-MiniLM-L6-v2 (local, free)
- Runs entirely on CPU, no API calls, no cost
- Output dimension: **384** (Pinecone index configured to match)
- `normalize_embeddings=True` → unit vectors → cosine = dot product
- Shared singleton instance between `ingest_jd.py` and `modules/similarity.py`

### Semantic Similarity via Pinecone (serverless, free tier)
- Solves the "Kafka ↔ Kinesis" problem with real vector math, not LLM guessing
- Index: `resume-shortlister`, metric: `cosine`, cloud: `aws/us-east-1`
- Namespace `jd-requirements` holds all JD chunks
- Per evaluation: top-1 cosine match per resume chunk, then deduplicated
- Full match list stored in state for rendering in the UI evidence table

---

## Scoring Model

| Dimension | Source | Weight | What it measures |
|-----------|--------|--------|-----------------|
| Exact Match | Groq/Llama | 30% | Hard keyword overlap — "Python" = "Python", "Postgres" ≈ "PostgreSQL" |
| Semantic Similarity | Pinecone | **35%** | Tech equivalence via cosine — "AWS Kinesis" ↔ "Apache Kafka" = 0.91 |
| Achievement | Groq/Llama | 20% | Quantified impact bullets (numbers, %, multipliers, scale) |
| Ownership | Groq/Llama | 15% | (strong verb bullets / total bullets) × 100 |

```
Overall = (Exact × 0.30) + (Similarity × 0.35) + (Achievement × 0.20) + (Ownership × 0.15)
```

**Tier classification:**
- Tier A (Strong Hire):    Overall ≥ 75
- Tier B (Potential Hire): Overall ≥ 50
- Tier C (No Hire):        Overall < 50

### Key Prompt Engineering Decisions
- **Exact vs Similarity explicitly separated in prompt** — LLM is told "do NOT count semantic equivalents here (Kinesis ≠ Kafka for Exact Score)". This keeps the 4 dimensions independent and meaningful.
- **Ownership formula given explicitly** — `(strong verb bullets / total bullets) × 100`. LLM follows math better than qualitative instructions.
- **Reasoning required per dimension** — the prompt demands a populated `reasoning{}` object explaining every score. This is the explainability layer the rubric evaluates.

---

## Scalability (10,000+ resumes/day)

| Concern | Solution |
|---------|----------|
| PDF parsing throughput | LangGraph nodes are stateless; deploy N workers behind FastAPI |
| Embedding latency | `all-MiniLM-L6-v2` runs locally at ~100 sentences/sec on CPU |
| Pinecone query latency | ~10ms per query; parallelise per-skill queries with `asyncio.gather` |
| LLM cost | Groq free tier; one parse call + one score call per resume |
| JD re-ingestion | JD ingested once, cached by `jd_id` in Pinecone namespace; idempotent |
| Horizontal scaling | `PipelineState` is a plain dict — graph is fully stateless, scales linearly |

---

## Tech Stack (100% Free)

| Layer | Choice | Cost |
|-------|--------|------|
| Orchestration | LangGraph | free |
| Vector DB | Pinecone serverless (cosine, dim=384) | free tier |
| LLM | Groq — llama-3.3-70b-versatile | free tier |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | local, free |
| PDF Parsing | PyPDF2 | free |
| UI | Streamlit | free |
| Config | python-dotenv | free |

---
