import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")      # used for embeddings only
PINECONE_API_KEY  = os.getenv("PINECONE_API_KEY", "")

# --- Pinecone ---
PINECONE_INDEX_NAME = "resume-shortlister"
PINECONE_DIMENSION  = 1536          # text-embedding-3-small output dim
PINECONE_METRIC     = "cosine"
PINECONE_CLOUD      = "aws"
PINECONE_REGION     = "us-east-1"

JD_NAMESPACE     = "jd-requirements"
RESUME_NAMESPACE = "resume-skills"

# --- Models ---
CLAUDE_MODEL    = "claude-opus-4-5"
EMBED_MODEL     = "text-embedding-3-small"

# --- Scoring weights (must sum to 1.0) ---
SCORE_WEIGHTS = {
    "exact":       0.30,
    "similarity":  0.35,   # highest weight — Pinecone does the heavy lifting
    "achievement": 0.20,
    "ownership":   0.15,
}

# --- Tier thresholds ---
TIER_THRESHOLDS = {
    "A": 75,   # overall >= 75
    "B": 50,   # 50 <= overall < 75
    "C": 0,    # overall < 50
}