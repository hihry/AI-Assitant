import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
# Groq: free tier at console.groq.com — no credit card needed
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")

# --- Pinecone ---
PINECONE_INDEX_NAME = "resume-shortlister"
PINECONE_DIMENSION  = 384           # all-MiniLM-L6-v2 output dim (local, free)
PINECONE_METRIC     = "cosine"
PINECONE_CLOUD      = "aws"
PINECONE_REGION     = "us-east-1"

JD_NAMESPACE     = "jd-requirements"
RESUME_NAMESPACE = "resume-skills"

# --- Models ---
# Groq free tier → llama-3.3-70b-versatile is the best free model
# for structured JSON generation tasks
GROQ_MODEL  = "llama-3.3-70b-versatile"

# sentence-transformers: runs locally on CPU, zero API cost
# all-MiniLM-L6-v2 → 384-dim, fast, strong semantic quality
EMBED_MODEL = "all-MiniLM-L6-v2"

# --- Scoring weights (must sum to 1.0) ---
SCORE_WEIGHTS = {
    "exact":       0.30,
    "similarity":  0.35,   # highest weight — Pinecone handles semantic match
    "achievement": 0.20,
    "ownership":   0.15,
}

# --- Tier thresholds ---
TIER_THRESHOLDS = {
    "A": 75,   # overall >= 75
    "B": 50,   # 50 <= overall < 75
    "C": 0,    # overall < 50
}