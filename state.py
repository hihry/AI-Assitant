"""Shared pipeline state definitions."""

from typing import TypedDict


class PipelineState(TypedDict, total=False):
    """State container passed between workflow nodes."""

    resume_text: str
    parsed_resume: dict
    job_description: dict
    similarity_results: list
    scores: dict
    verification: dict
    interview_questions: list
