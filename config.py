"""Runtime configuration and API keys.

Populate values from environment variables before use.
"""

import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
