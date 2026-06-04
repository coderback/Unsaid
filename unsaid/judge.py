"""
Claude Opus judge: classify each Year-1 disclosure unit against its Year-2 candidates.
Rule 1: embeddings align, Claude judges — cosine similarity never makes the final call.
"""
import os
import logging
import time
from typing import List, Dict, Tuple, Optional

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

CLASSIFY_TOOL = {
    "name": "classify_change",
    "description": (
        "Classify how a Year-1 disclosure unit changed (or disappeared) in Year-2. "
        "Focus ONLY on the underlying economic risk, not prose style."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "string",
                "enum": ["RETAINED", "REWORDED", "SOFTENED", "REMOVED", "ABSORBED"],
                "description": (
                    "RETAINED: same risk, materially same language. "
                    "REWORDED: same risk, different wording (not a signal). "
                    "SOFTENED: risk downgraded, hedged, or qualifiers weakened (a signal). "
                    "REMOVED: genuinely absent from Year-2 (strong signal). "
                    "ABSORBED: folded into a broader Year-2 disclosure."
                ),
            },
            "year1_quote": {
                "type": "string",
                "description": "The most salient verbatim excerpt from the Year-1 unit (≤300 chars).",
            },
            "year2_quote_or_null": {
                "type": ["string", "null"],
                "description": "Corresponding verbatim excerpt from Year-2 (null if REMOVED).",
            },
            "reasoning": {
                "type": "string",
                "description": "1–2 sentences explaining the classification decision.",
            },
            "section": {
                "type": "string",
                "description": "Source section: '1A' or '7A'.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confidence in the classification (0.0–1.0).",
            },
        },
        "required": [
            "classification",
            "year1_quote",
            "year2_quote_or_null",
            "reasoning",
            "section",
            "confidence",
        ],
    },
}

_SYSTEM_PROMPT = (
    "You are an expert financial analyst reviewing year-over-year changes in SEC 10-K "
    "risk disclosures. Your job is to classify whether a Year-1 risk disclosure "
    "was retained, reworded, softened, removed, or absorbed into another section "
    "in Year-2.\n\n"
    "Critical instructions:\n"
    "1. Focus ONLY on the underlying ECONOMIC RISK being disclosed — ignore cosmetic "
    "   prose changes, boilerplate reformatting, or section restructuring.\n"
    "2. Treat negation as material: 'we are no longer exposed to X' vs 'we are exposed "
    "   to X' is a SOFTENED or REMOVED classification, not a reword.\n"
    "3. Treat weakened qualifiers as material: replacing 'significant' with 'some' is "
    "   SOFTENED.\n"
    "4. If none of the Year-2 candidates meaningfully addresses the Year-1 risk, "
    "   classify as REMOVED.\n"
    "5. ABSORBED means the same risk exists but is now bundled into a broader disclosure "
    "   — note which Year-2 unit absorbed it.\n"
    "6. Provide a verbatim year1_quote (the most salient sentence or clause, ≤300 chars).\n"
    "7. Confidence: 0.9+ only if you are certain; use 0.7–0.9 for reasonable inference."
)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _build_judge_prompt(
    y1_unit: Dict,
    candidates: List[Tuple[Dict, float]],
    year1: int,
    year2: int,
) -> str:
    section = y1_unit.get("section", "?")
    title = y1_unit.get("title", "Untitled")
    text = y1_unit.get("text", "")

    lines = [
        f"## Year-{year1} Disclosure (Item {section}): {title}",
        "",
        text,
        "",
        "---",
        "",
    ]

    if candidates:
        lines.append(f"## Year-{year2} Candidate Disclosures (top {len(candidates)} by semantic similarity)")
        lines.append("")
        for rank, (c_unit, sim) in enumerate(candidates, 1):
            c_title = c_unit.get("title", "Untitled")
            c_text = c_unit.get("text", "")
            c_section = c_unit.get("section", "?")
            lines.append(f"### Candidate {rank} (Item {c_section}, similarity={sim:.2f}): {c_title}")
            lines.append("")
            lines.append(c_text)
            lines.append("")
    else:
        lines.append(
            f"## Year-{year2} Candidates: NONE FOUND\n"
            "No Year-2 disclosure is semantically similar to this Year-1 unit. "
            "This strongly suggests the risk was REMOVED."
        )

    lines += [
        "---",
        "",
        f"Classify how the Year-{year1} disclosure changed in Year-{year2}. "
        "Remember: focus on economic substance, not prose style.",
    ]

    return "\n".join(lines)


def judge_unit(
    y1_unit: Dict,
    candidates: List[Tuple[Dict, float]],
    year1: int,
    year2: int,
    retries: int = 2,
) -> Dict:
    """
    Ask Claude Opus to classify one Year-1 unit against its Year-2 candidates.
    Returns a dict with all classify_change fields plus the original unit id and title.
    """
    client = _get_client()
    prompt = _build_judge_prompt(y1_unit, candidates, year1, year2)

    for attempt in range(retries + 1):
        try:
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                tools=[CLASSIFY_TOOL],
                tool_choice={"type": "any"},
                messages=[{"role": "user", "content": prompt}],
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "classify_change":
                    result = dict(block.input)
                    result["id"] = y1_unit.get("id", "unknown")
                    result["title"] = y1_unit.get("title", "Untitled")
                    # Ensure section is taken from the unit if model omits it
                    if not result.get("section"):
                        result["section"] = y1_unit.get("section", "?")
                    logger.info(
                        "Judged '%s' → %s (conf=%.2f)",
                        result["title"][:60],
                        result["classification"],
                        result.get("confidence", 0),
                    )
                    return result

            logger.warning("Judge returned no tool_use block on attempt %d", attempt + 1)
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            logger.warning("Rate limit hit; waiting %ds …", wait)
            time.sleep(wait)
        except Exception as e:
            logger.error("Judge error on attempt %d: %s", attempt + 1, e)
            if attempt == retries:
                raise

    # If all retries failed, return a fallback RETAINED
    return {
        "id": y1_unit.get("id", "unknown"),
        "title": y1_unit.get("title", "Untitled"),
        "classification": "RETAINED",
        "year1_quote": y1_unit.get("text", "")[:300],
        "year2_quote_or_null": None,
        "reasoning": "Classification failed after retries; defaulted to RETAINED.",
        "section": y1_unit.get("section", "?"),
        "confidence": 0.0,
    }


def judge_new_unit(y2_unit: Dict, year2: int) -> Dict:
    """Build a NEW classification record for an orphaned Year-2 unit."""
    return {
        "id": y2_unit.get("id", "unknown"),
        "title": y2_unit.get("title", "Untitled"),
        "classification": "NEW",
        "year1_quote": None,
        "year2_quote_or_null": y2_unit.get("text", "")[:300],
        "reasoning": "No matching Year-1 disclosure found; this risk was first disclosed in Year-2.",
        "section": y2_unit.get("section", "?"),
        "confidence": 0.85,
    }


def judge_all(
    y1_units: List[Dict],
    candidates_per_y1: List[List[Tuple[Dict, float]]],
    new_candidates: List[Dict],
    year1: int,
    year2: int,
) -> List[Dict]:
    """
    Run the judge over all Year-1 units and all NEW Year-2 candidates.
    Returns a flat list of classification dicts.
    """
    results: List[Dict] = []

    total = len(y1_units)
    for i, (y1_unit, candidates) in enumerate(zip(y1_units, candidates_per_y1)):
        logger.info("Judging unit %d/%d: %s", i + 1, total, y1_unit.get("title", "?")[:60])
        # Filter candidates to those with at least minimal similarity (don't noise the judge)
        strong_candidates = [(u, s) for u, s in candidates if s >= 0.20]
        result = judge_unit(y1_unit, strong_candidates, year1, year2)
        results.append(result)

    for y2_unit in new_candidates:
        results.append(judge_new_unit(y2_unit, year2))

    return results
