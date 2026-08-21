"""
Segment a section's prose text into discrete disclosure units via Claude Sonnet.
Each unit: {id, title, text, section}
"""
import os
import json
import logging
from typing import List, Dict, Optional

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

SEGMENT_TOOL = {
    "name": "segment_disclosures",
    "description": (
        "Split a 10-K section's text into discrete, self-contained disclosure units. "
        "Each unit should represent one coherent risk or topic — not a sentence, "
        "but a complete idea (typically 1–5 paragraphs). "
        "Preserve quantitative details verbatim."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "units": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":    {"type": "string", "description": "Short slug, e.g. 'interest_rate_risk'"},
                        "title": {"type": "string", "description": "Brief descriptive title (5–10 words)"},
                        "text":  {"type": "string", "description": "Full verbatim text of this disclosure unit"},
                    },
                    "required": ["id", "title", "text"],
                },
            }
        },
        "required": ["units"],
    },
}

_SYSTEM_PROMPT = (
    "You are a financial analyst parsing SEC 10-K filings. "
    "Your task: segment the provided section text into discrete, self-contained "
    "disclosure units for year-over-year comparison. "
    "Rules:\n"
    "- Each unit covers one coherent risk or topic.\n"
    "- Do NOT split mid-paragraph; keep related sentences together.\n"
    "- Preserve all quantitative figures exactly as written.\n"
    "- Titles should be concise and descriptive (e.g. 'Interest Rate Risk — EVE Sensitivity').\n"
    "- Aim for 5–30 units per section depending on length.\n"
    "- Do NOT summarize; capture the full text of each unit."
)

_MAX_SECTION_CHARS = 40_000  # ~10k tokens; chunk if longer


def _get_client(api_key: Optional[str] = None) -> anthropic.Anthropic:
    global _client
    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=key)
    return _client


def _segment_chunk(text: str, section_label: str, chunk_idx: int, api_key: Optional[str] = None) -> List[Dict]:
    """Call Claude Sonnet to segment one chunk of text."""
    client = _get_client(api_key)

    prompt = (
        f"Segment the following Item {section_label} text from a 10-K filing "
        f"into discrete disclosure units.\n\n"
        f"--- BEGIN TEXT ---\n{text}\n--- END TEXT ---"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=_SYSTEM_PROMPT,
        tools=[SEGMENT_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract tool_use block
    for block in response.content:
        if block.type == "tool_use" and block.name == "segment_disclosures":
            units = block.input.get("units", [])
            # Tag each unit with a chunk-scoped id to avoid collisions
            for i, u in enumerate(units):
                u["id"] = f"{section_label}_{chunk_idx}_{i:03d}_{u.get('id', 'unit')}"
            logger.info(
                "Segmented Item %s chunk %d → %d units",
                section_label, chunk_idx, len(units)
            )
            return units

    logger.warning("Segmentation returned no tool_use block for chunk %d", chunk_idx)
    return []


def segment_section(text: str, section_label: str, api_key: Optional[str] = None) -> List[Dict]:
    """
    Segment a full section text into disclosure units.
    Chunks the text if it exceeds the per-call limit.
    Returns list of {id, title, text, section}.
    """
    if not text or not text.strip():
        logger.warning("Empty text for section %s, skipping segmentation", section_label)
        return []

    # Split into chunks by paragraph boundaries if text is very long
    chunks: List[str] = []
    if len(text) <= _MAX_SECTION_CHARS:
        chunks = [text]
    else:
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > _MAX_SECTION_CHARS and current:
                chunks.append(current.strip())
                current = para
            else:
                current += "\n\n" + para
        if current.strip():
            chunks.append(current.strip())

    all_units: List[Dict] = []
    for idx, chunk in enumerate(chunks):
        units = _segment_chunk(chunk, section_label, idx, api_key=api_key)
        for u in units:
            u["section"] = section_label  # attach source section
        all_units.extend(units)

    logger.info(
        "Section %s: %d total units from %d chunk(s)",
        section_label, len(all_units), len(chunks)
    )
    return all_units


def segment_all_sections(sections: Dict[str, str | None], api_key: Optional[str] = None) -> List[Dict]:
    """
    Segment both 1A and 7A sections.
    sections = {"1A": text_or_none, "7A": text_or_none}
    Returns flat list of units with section label attached.
    """
    all_units: List[Dict] = []
    for label, text in sections.items():
        if text:
            units = segment_section(text, label, api_key=api_key)
            all_units.extend(units)
        else:
            logger.warning("No text available for section %s", label)
    return all_units
