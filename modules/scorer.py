"""Candidate scoring via exact match, achievements, and ownership signals."""


def score_candidate(parsed_resume: dict, jd_context: dict) -> dict:
    """Score a candidate against the target job description."""
    raise NotImplementedError("Implement candidate scoring in modules/scorer.py")
