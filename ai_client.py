"""Opt-in LLM interpretation of small aggregated evidence packets.

No raw company files or transaction rows are sent. No API request is made
until the user explicitly presses the generate button in Streamlit.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://api.openai.com/v1/responses"


def available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def extract_text(response: dict) -> str:
    chunks = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    chunks.append(part["text"])
    return "\n".join(chunks).strip()


def generate_explanation(evidence: dict, *, audience: str, timeout: int = 30) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    if not isinstance(evidence, dict) or "summary" not in evidence or "signals" not in evidence:
        raise ValueError("Only validated aggregate evidence packets are accepted")
    instructions = (
        "You are a cautious bilingual finance business partner. "
        "Only use the supplied aggregated facts. Never invent amounts, causality, elasticity, "
        "ROI, or unobserved root causes. Separate observed facts, hypotheses to test, "
        "recommended checks/actions, and risks. Cite each numerical claim to the named "
        "metric in the evidence packet. Do not recommend automatic financial postings or "
        "price changes. Respond concisely in Chinese with key English finance terms."
    )
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-6-luna"),
        "instructions": instructions,
        "input": json.dumps({"audience": audience, "facts": evidence}, ensure_ascii=False),
        "store": False,
        "max_output_tokens": 1000,
    }
    request = Request(
        API_URL, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"AI request failed with HTTP {exc.code}") from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("AI request could not complete; check network and API access") from exc
    output = extract_text(data)
    if not output:
        raise RuntimeError("Model returned no text")
    return output
