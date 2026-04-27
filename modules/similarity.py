"""Similarity query node for Pinecone candidate matching."""


def query_similarity(parsed_resume: dict, top_k: int = 5) -> list:
    """Return nearest job-description matches for a parsed resume."""
    raise NotImplementedError("Implement similarity query in modules/similarity.py")
