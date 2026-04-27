# AI Resume Shortlisting System — Architecture Document

## Overview
An end-to-end pipeline that evaluates candidates by comparing resumes against a Job Description (JD) using semantic vector search (Pinecone) and LLM reasoning (Claude), orchestrated via LangGraph.

---

## System Architecture

```
JD Ingestion (one-time per JD)
────────────────────────────────────────────────
JD Text → Chunk by requirement → Embed (OpenAI) → Upsert to Pinecone [jd-requirements namespace]

Resume Evaluation Pipeline (per candidate)
────────────────────────────────────────────────
PDF Resume
    │
    ▼
[Node 1: parse_resume]
    Claude extracts structured JSON
    {name, skills[], projects[], experience_years, links{}}
    │
    ▼
[Node 2: similarity_search]
    Each resume skill/project chunk → embed → query Pinecone
    Returns: [{resume_chunk, jd_match, cosine_score}]
    Similarity Score = avg(top cosine scores) × 100
    │
    ▼
[Node 3: scorer]
    Claude computes:
      - Exact Score:       keyword overlap count vs JD requirements
      - Achievement Score: quantified impact bullets (numbers, %)
      - Ownership Score:   action verb analysis (built/led/owned vs assisted/helped)
    Pinecone provides:
      - Similarity Score:  already computed in Node 2
    Final: weighted average → overall score
    │
    ▼
[Node 4: build_report]
    Assembles final JSON report with all scores + reasoning + flags
    │
    ▼
Streamlit UI renders the report
```

---

## Data Strategy

### PDF → Structured JSON
- `PyPDF2` extracts raw text from PDF bytes
- Claude (`claude-opus-4-5`) parses the raw text into a strict JSON schema
- The schema is enforced via a system prompt that demands JSON-only output

### Chunking Strategy for JD
- Each requirement bullet = one chunk
- Each responsibility bullet = one chunk
- Chunks are short (one sentence) to maximize embedding precision

### Chunking Strategy for Resume
- Each skill = one chunk
- Each project description = one chunk
- Combined skill+tech tags = one chunk per project

---

## AI Strategy

### LLM: Claude (claude-opus-4-5)
Used for:
- Resume parsing (unstructured PDF → structured JSON)
- Exact score: counting hard-skill matches against JD
- Achievement score: detecting quantified impact
- Ownership score: analyzing verb strength per project bullet
- Explainability: generating human-readable reasoning for every score

### Embedding Model: OpenAI text-embedding-3-small
Used for:
- Embedding JD requirement chunks (ingestion)
- Embedding resume skill/project chunks (per evaluation)
- Dimension: 1536, Metric: cosine

### Semantic Similarity via Pinecone
- Solves the "Kafka ↔ Kinesis" problem with real vector math, not LLM guessing
- Each resume chunk is queried against the JD namespace
- Top-1 cosine match per chunk is recorded with the matched JD text (explainability)
- Similarity Score = average of top cosine scores × 100

---

## Scoring Model

| Dimension | Source | Weight | What it measures |
|-----------|--------|--------|-----------------|
| Exact Score | Claude | 30% | Hard keyword overlap (Python, Docker, etc.) |
| Similarity Score | Pinecone | 35% | Semantic tech equivalence (Kinesis ↔ Kafka) |
| Achievement Score | Claude | 20% | Quantified impact bullets |
| Ownership Score | Claude | 15% | "Built/Led/Owned" vs "Assisted/Helped" |

**Overall = weighted sum of all four**

---

## Scalability (10,000+ resumes/day)

| Concern | Solution |
|---------|----------|
| PDF parsing throughput | Async LangGraph nodes; batch Claude API calls |
| Pinecone query latency | ~10ms per query; parallelise per-skill queries with asyncio.gather |
| LLM cost | Claude called once per resume (single prompt handles 3 scores); Pinecone handles similarity |
| JD re-ingestion | JD ingested once; cached by jd_id in Pinecone namespace |
| Horizontal scaling | LangGraph graph is stateless; deploy behind a FastAPI server with worker pool |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Orchestration | LangGraph |
| Vector DB | Pinecone (serverless, cosine) |
| LLM | Anthropic Claude claude-opus-4-5 |
| Embeddings | OpenAI text-embedding-3-small |
| PDF Parsing | PyPDF2 |
| UI | Streamlit |
| Config | python-dotenv |