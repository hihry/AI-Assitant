# AI Resume Shortlister

An end-to-end AI-assisted resume screening app that compares a candidate resume against a Job Description (JD), computes a multi-dimensional score, and renders a visual report in Streamlit.

The project combines:
- LLM extraction and scoring via Groq
- Semantic matching via local embeddings + Pinecone
- Workflow orchestration via LangGraph
- Human-friendly report rendering via Streamlit

## What This Project Does

For each candidate resume PDF:
1. Parses the PDF and extracts structured resume JSON.
2. Computes semantic similarity between resume chunks and JD requirements using Pinecone.
3. Computes exact match, achievement, and ownership dimensions via LLM.
4. Combines all dimensions into a weighted overall score.
5. Produces a final structured report and renders it in the UI.

## Tech Stack

- Python 3.10+ (recommended)
- Streamlit (UI)
- LangGraph (pipeline orchestration)
- Groq API (LLM calls)
- sentence-transformers (`all-MiniLM-L6-v2`) for local embeddings
- Pinecone (vector database)
- PyPDF2 (PDF text extraction)
- python-dotenv (environment config)

## Repository Structure

- [main.py](main.py): Streamlit UI and pipeline trigger
- [graph.py](graph.py): LangGraph pipeline wiring
- [config.py](config.py): runtime config, model choices, weights, thresholds
- [state.py](state.py): shared pipeline state schema
- [modules/parse_resume.py](modules/parse_resume.py): resume PDF -> structured JSON
- [modules/similarity.py](modules/similarity.py): semantic retrieval + similarity score
- [modules/scorer.py](modules/scorer.py): LLM-based exact/achievement/ownership scoring
- [modules/build_report.py](modules/build_report.py): final UI-ready report assembly
- [modules/ingest_jd.py](modules/ingest_jd.py): JD chunking + embedding + upsert into Pinecone
- [prompts/parse_resume.txt](prompts/parse_resume.txt): parser prompt template
- [prompts/score_candidate.txt](prompts/score_candidate.txt): scoring prompt template
- [sample_data/jd_sample.json](sample_data/jd_sample.json): example JD
- [sample_data/resume_sample.pdf](sample_data/resume_sample.pdf): example resume

## Design Decisions

### 1. Linear Orchestration Graph
The pipeline is intentionally linear and explainable:

`parse_resume -> similarity_search -> scorer -> build_report`

Rationale:
- Easy to debug node-by-node.
- Deterministic execution order.
- Clear ownership of transformations at each stage.

### 2. Hybrid Scoring (LLM + Vector Search)
The scoring system uses 4 dimensions:
- Exact match (LLM)
- Semantic similarity (Pinecone)
- Achievement evidence (LLM)
- Ownership strength (LLM)

Configured in [config.py](config.py):
- exact: 30%
- similarity: 35%
- achievement: 20%
- ownership: 15%

Why hybrid:
- LLM handles nuanced language/reasoning.
- Pinecone handles semantic equivalence (e.g., related technologies).
- Weighted fusion gives a balanced ranking signal.

### 3. Local Embeddings
Embeddings are generated locally using `all-MiniLM-L6-v2`.

Why:
- Lower cost (no embedding API calls).
- Fast enough for local/dev use.
- Stable vector dimension (384) mapped to Pinecone index config.

### 4. UI Stability First
The Streamlit frontend layout/colors are preserved while wiring real graph output.
Mock data acts as a fallback before first successful run.

## Local Setup

## 1) Clone and enter the project
```powershell
git clone <your-repo-url>
cd resume-shortlister
```

## 2) Create and activate a virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If execution policy blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 3) Install dependencies
```powershell
pip install -r requirements.txt
```

## 4) Create environment file
Create [ .env ] using [ .env.example ] as template and fill real keys:

```env
GROQ_API_KEY=your_groq_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
```

Required variables used by [config.py](config.py):
- `GROQ_API_KEY`
- `PINECONE_API_KEY`

## 5) (One-time per JD) Ingest the JD into Pinecone
```powershell
python -m modules.ingest_jd --jd sample_data/jd_sample.json
```

This creates/uses index `resume-shortlister` and upserts JD chunks into namespace `jd-requirements`.

## 6) Run the Streamlit app
```powershell
streamlit run main.py
```

In the UI:
- Expand Run Real Evaluation.
- Upload a resume PDF.
- Review/edit JD JSON.
- Click Run Pipeline.

## Optional CLI Checks

## Parse only
```powershell
python -m modules.parse_resume sample_data/resume_sample.pdf
```

## Graph end-to-end smoke test
```powershell
python graph.py
```

## How Data Flows

Input state fields:
- `jd_text` (JSON string or text)
- `pdf_bytes`

Node outputs:
- parse_resume -> `resume_json`
- similarity_search -> `pinecone_matches`, partial `score_result`
- scorer -> full `score_result`
- build_report -> `final_report`

The UI reads `final_report` and renders:
- candidate profile
- 4D score breakdown
- semantic matches table
- flags and extracted skills

## Configuration

Core knobs are in [config.py](config.py):
- model IDs (`GROQ_MODEL`, `EMBED_MODEL`)
- Pinecone index/namespace settings
- score weights
- tier thresholds

When changing embedding model/dimension, keep Pinecone index dimension aligned.

## Troubleshooting

## 1) `ModuleNotFoundError: No module named 'config'`
Use module-style execution from repo root:
- `python -m modules.ingest_jd ...`
- `python -m modules.parse_resume ...`

## 2) `FileNotFoundError` for prompt files
Ensure prompts exist under [prompts](prompts) and parser/scorer resolve project-root paths.

## 3) Streamlit torch watcher error (`torch.classes` / `__path__._path`)
This repo includes [ .streamlit/config.toml ] with file watcher disabled.
Restart Streamlit after config changes.

## 4) UnicodeDecodeError reading prompt/JD files on Windows
Use UTF-8 reads in file-loading code (already applied in scorer paths).

## 5) Pinecone index issues
- Verify `PINECONE_API_KEY` is valid.
- Confirm index region/cloud in [config.py](config.py) matches your Pinecone project.
- Re-run ingestion after changing JD.

## Security Notes

- Never commit real secrets.
- Keep [.env](.env) untracked.
- Keep [.env.example](.env.example) sanitized.

## Current Limitations

- Single-candidate, one-run-at-a-time UI interaction.
- Assumes text-extractable PDFs (image-only PDFs may fail extraction).
- Quality depends on prompt design and JD chunking quality.

## Suggested Next Improvements

1. Add persistent report export (JSON/CSV/HTML).
2. Add batch resume processing.
3. Add retry/error classification around external API calls.
4. Add unit tests for node-level functions.
5. Add API layer (FastAPI) for service integration.

## License

Add your preferred license here (MIT, Apache-2.0, etc.).
