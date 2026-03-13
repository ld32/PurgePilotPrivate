"""Send a file/folder list to an LLM server and parse purge confidence scores."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from .scanner import ScanResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PurgeEstimate:
    """Purge confidence estimate for a single path."""

    path: str
    confidence: float  # 0.0 (keep) → 1.0 (definitely purge)
    reason: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class PurgeReport:
    """Full purge report returned by the LLM client."""

    root: str
    estimates: List[PurgeEstimate]

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "estimates": [e.to_dict() for e in self.estimates],
        }

    def high_confidence(self, threshold: float = 0.7) -> List[PurgeEstimate]:
        """Return entries whose confidence is at or above *threshold*."""
        return [e for e in self.estimates if e.confidence >= threshold]


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a disk-space management assistant.
You will receive a JSON list of files and directories from a user's data folder.
For each entry evaluate how safe it is to delete it and return a JSON array.

Each element in the response array must have exactly these keys:
  "path"       – the exact path string from the input
  "confidence" – a float between 0.0 (definitely keep) and 1.0 (definitely purge)
  "reason"     – one concise sentence explaining the decision

Respond with ONLY the JSON array and nothing else."""


def estimate_purge_confidence(
    scan_result: ScanResult,
    *,
    api_url: str,
    model: str,
    api_key: Optional[str] = None,
    timeout: int = 120,
    system_prompt: str = _SYSTEM_PROMPT,
) -> PurgeReport:
    """Call the LLM server and return a :class:`PurgeReport`.

    Parameters
    ----------
    scan_result:
        Result produced by :func:`~purge_pilot.scanner.scan_directory`.
    api_url:
        Base URL of an OpenAI-compatible chat-completions endpoint,
        e.g. ``"http://localhost:11434/v1"`` for a local Ollama server
        or ``"https://api.openai.com/v1"`` for the OpenAI API.
    model:
        Model name to use, e.g. ``"gpt-4o"`` or ``"llama3"``.
    api_key:
        Optional bearer token. Pass ``None`` for servers that don't require
        authentication (e.g. a local Ollama instance).
    timeout:
        HTTP request timeout in seconds.
    system_prompt:
        The system prompt to use for the LLM.
    """
    entries_json = json.dumps(
        [e.to_dict() for e in scan_result.entries],
        indent=2,
    )

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": entries_json},
        ],
        "temperature": 0.2,
    }

    endpoint = api_url.rstrip("/") + "/chat/completions"
    logger.debug("POST %s  model=%s  entries=%d", endpoint, model, len(scan_result.entries))

    response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()

    raw = response.json()
    content = raw["choices"][0]["message"]["content"]
    estimates = _parse_estimates(content)

    return PurgeReport(root=scan_result.root, estimates=estimates)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_estimates(content: str) -> List[PurgeEstimate]:
    """Parse the LLM response content into a list of :class:`PurgeEstimate`."""
    content = content.strip()

    # Strip optional markdown code fences
    if content.startswith("```"):
        lines = content.splitlines()
        # Remove opening fence (e.g. ```json) and closing fence
        lines = [l for l in lines if not l.startswith("```")]
        content = "\n".join(lines)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON content: {content!r}") from exc

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array from LLM, got: {type(data).__name__}")

    estimates: List[PurgeEstimate] = []
    for item in data:
        try:
            confidence = float(item["confidence"])
            confidence = max(0.0, min(1.0, confidence))  # clamp to [0, 1]
            estimates.append(
                PurgeEstimate(
                    path=str(item["path"]),
                    confidence=confidence,
                    reason=str(item.get("reason", "")),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed LLM response item %r: %s", item, exc)

    return estimates
