"""
parse_resume.py
───────────────
LangGraph Node 1: PDF bytes → structured ResumeJSON

Pipeline position:
    [parse_resume] → similarity_search → scorer → build_report

What it does:
    1. Extracts raw text from PDF bytes using PyPDF2
    2. Sends text to Groq (llama-3.3-70b-versatile) with a strict JSON prompt
    3. Validates the returned JSON matches the expected schema
    4. Writes result into PipelineState["resume_json"]
"""

import json
import re
from pathlib import Path

import PyPDF2
from groq import Groq

import config
from state import PipelineState


# ── Groq client (singleton) ───────────────────────────────────────────────────
_groq_client: Groq | None = None

def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


# ── Prompt loader ─────────────────────────────────────────────────────────────
def load_prompt(resume_text: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / "parse_resume.txt"
    template = prompt_path.read_text()
    return template.replace("{resume_text}", resume_text)


# ── PDF extraction ────────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract raw text from PDF bytes using PyPDF2.
    Joins all pages with newlines, strips excessive whitespace.
    """
    import io
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))

    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())

    full_text = "\n\n".join(pages)

    # Collapse 3+ newlines → 2 newlines for cleaner LLM input
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    return full_text.strip()


# ── JSON extraction from LLM response ────────────────────────────────────────
def extract_json(raw: str) -> dict:
    """
    Robustly extract a JSON object from LLM output.
    Handles cases where the model wraps output in ```json fences despite instructions.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Find first { ... } block
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM response:\n{raw[:300]}")

    return json.loads(cleaned[start:end])


# ── Schema validation ─────────────────────────────────────────────────────────
def validate_and_fill(parsed: dict) -> dict:
    """
    Ensure required keys exist with correct types.
    Fills missing fields with safe defaults so downstream nodes never KeyError.
    """
    defaults = {
        "name":              "Unknown",
        "email":             None,
        "experience_years":  0,
        "skills":            [],
        "projects":          [],
        "links":             {"github": None, "linkedin": None},
        "raw_skills_section": None,
    }

    for key, default in defaults.items():
        if key not in parsed or parsed[key] is None:
            parsed[key] = default

    # Ensure projects have sub-fields
    for project in parsed.get("projects", []):
        project.setdefault("title",            "Untitled")
        project.setdefault("description",      "")
        project.setdefault("tech",             [])
        project.setdefault("ownership_verbs",  [])
        project.setdefault("achievement_bullets", [])

    # Ensure links sub-keys exist
    parsed["links"].setdefault("github",   None)
    parsed["links"].setdefault("linkedin", None)

    return parsed


# ── Core function ─────────────────────────────────────────────────────────────
def parse_resume(pdf_bytes: bytes) -> dict:
    """
    Parse a PDF resume into structured JSON.

    Args:
        pdf_bytes: raw bytes of the uploaded PDF

    Returns:
        resume_json dict matching the schema in state.py
    """
    print("[parse] Extracting text from PDF...")
    raw_text = extract_text_from_pdf(pdf_bytes)
    print(f"[parse] Extracted {len(raw_text)} characters across {raw_text.count(chr(12)) + 1} page(s).")

    if not raw_text.strip():
        raise ValueError("PDF appears to be empty or image-only (no extractable text).")

    print("[parse] Sending to Groq for structured extraction...")
    prompt = load_prompt(raw_text)

    client   = get_groq_client()
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise resume parser. "
                    "You ALWAYS respond with only a valid JSON object. "
                    "No markdown, no explanation, no extra text."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.0,     # deterministic — parsing should not be creative
        max_tokens=2048,
    )

    raw_output = response.choices[0].message.content
    print("[parse] Received LLM response. Extracting JSON...")

    try:
        parsed = extract_json(raw_output)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"[parse] Failed to parse LLM output as JSON: {e}\nRaw output:\n{raw_output[:500]}")

    # Add raw text to state so scorer has full context
    parsed["raw_text"] = raw_text

    result = validate_and_fill(parsed)
    print(f"[parse] ✓ Parsed resume for: '{result['name']}' | "
          f"Skills: {len(result['skills'])} | "
          f"Projects: {len(result['projects'])} | "
          f"Experience: {result['experience_years']} yr(s)")

    return result


# ── LangGraph node wrapper ────────────────────────────────────────────────────
def parse_resume_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node. Reads pdf_bytes from state, writes resume_json back.
    """
    resume_json = parse_resume(state["pdf_bytes"])
    return {**state, "resume_json": resume_json}


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python modules/parse_resume.py <path_to_resume.pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    pdf_bytes = pdf_path.read_bytes()
    result    = parse_resume(pdf_bytes)

    print("\n── Parsed Resume JSON ──────────────────────────")
    print(json.dumps(result, indent=2))