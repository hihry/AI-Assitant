"""Ingest a job description into Pinecone (run once per JD)."""


def ingest_job_description(jd_payload: dict) -> None:
    """Embed and upsert a job description into the vector store."""
    raise NotImplementedError("Implement JD ingestion in modules/ingest_jd.py")
