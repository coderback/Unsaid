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


class JudgeFailureRateExceeded(RuntimeError):
    """Raised when too many judge calls fall back, meaning the run is not trustworthy."""


# A run in which many judge calls fail produces a complete, plausible-looking
# analysis in which everything is RETAINED. That is indistinguishable from a real
# null result downstream, so the run must abort rather than be cached.
MAX_FALLBACK_RATE = 0.10
MIN_UNITS_BEFORE_RATE_CHECK = 5

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
                    "RETAINED: same risk, materially same substance and specificity. "
                    "REWORDED: same risk and same specifics, different wording (not a signal). "
                    "SOFTENED: risk downgraded, hedged, qualifiers weakened, OR specific "
                    "quantitative disclosure dropped while the topic survives (a signal). "
                    "REMOVED: the specific risk disclosure is absent from Year-2 (strong signal). "
                    "ABSORBED: the SAME substance, including its specifics, is fully present "
                    "inside a broader Year-2 disclosure, not merely the same topic."
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
    "5. ABSORBED is a HIGH bar: the same substance, including any quantitative "
    "   specifics, must genuinely appear inside a broader Year-2 disclosure. Note which "
    "   Year-2 unit absorbed it. A Year-2 unit that merely discusses the same TOPIC is "
    "   NOT absorption.\n"
    "5a. CRITICAL - do not let a topically-similar candidate mask a real loss. The "
    "   candidates below are retrieved by semantic similarity, so a related Year-2 unit "
    "   almost always exists. Similarity of topic is not continuity of disclosure. Ask "
    "   what a reader LOSES going from Year-1 to Year-2, not whether the subject is "
    "   still mentioned.\n"
    "5b. Dropping quantified disclosure is material even when the topic persists. If "
    "   Year-1 gave a figure, table, sensitivity metric or named exposure and Year-2 "
    "   gives only qualitative discussion, that is SOFTENED at minimum, never RETAINED, "
    "   REWORDED or ABSORBED. If a table column or scenario is dropped, classify on the "
    "   dropped component.\n"
    "5c. CONSISTENCY CHECK - if your own reasoning would say the Year-1 content is no "
    "   longer presented, no longer disclosed, omitted, not repeated or absent, then the "
    "   correct classification is SOFTENED or REMOVED, never RETAINED or ABSORBED. Your "
    "   label must match your reasoning.\n"
    "6. Provide a verbatim year1_quote (the most salient sentence or clause, ≤300 chars).\n"
    "7. Confidence: 0.9+ only if you are certain; use 0.7–0.9 for reasonable inference."
)


from typing import List, Dict, Tuple, Optional, Callable
from unsaid.llm import call_structured_tool, get_default_model


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
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    azure_api_version: Optional[str] = None,
    retries: int = 2,
) -> Dict:
    """
    Ask LLM judge (Claude Opus or Azure AI Foundry model e.g. gpt-5.6-luna) to classify
    one Year-1 unit against its Year-2 candidates.
    """
    target_model = model or get_default_model(provider, "judge")
    prompt = _build_judge_prompt(y1_unit, candidates, year1, year2)

    try:
        data = call_structured_tool(
            provider=provider,
            model=target_model,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
            tool_name="classify_change",
            tool_description="Classify how a Year-1 disclosure unit changed in Year-2 based on economic risk.",
            parameters_schema=CLASSIFY_TOOL["input_schema"],
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            azure_api_version=azure_api_version,
            max_tokens=2048,
            retries=retries,
        )

        result = dict(data)
        result["id"] = y1_unit.get("id", "unknown")
        result["title"] = y1_unit.get("title", "Untitled")
        if not result.get("section"):
            result["section"] = y1_unit.get("section", "?")

        logger.info(
            "Judged '%s' → %s (conf=%.2f, via %s/%s)",
            result["title"][:60],
            result["classification"],
            result.get("confidence", 0),
            provider,
            target_model,
        )
        return result
    except Exception as e:
        logger.error("Judge error (%s/%s): %s", provider, target_model, e)
        # Fallback RETAINED if model call completely fails
        return {
            "id": y1_unit.get("id", "unknown"),
            "title": y1_unit.get("title", "Untitled"),
            "classification": "RETAINED",
            "year1_quote": y1_unit.get("text", "")[:300],
            "year2_quote_or_null": None,
            "reasoning": f"Classification failed ({provider}/{target_model}); defaulted to RETAINED.",
            "section": y1_unit.get("section", "?"),
            "confidence": 0.0,
            # Explicit marker so judge_all can count these and abort a degraded run.
            "judge_failed": True,
            "judge_error": f"{type(e).__name__}: {e}"[:300],
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
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    azure_api_version: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[Dict]:
    """
    Run the judge over all Year-1 units and all NEW Year-2 candidates.
    Returns a flat list of classification dicts.
    """
    results: List[Dict] = []

    total = len(y1_units)
    for i, (y1_unit, candidates) in enumerate(zip(y1_units, candidates_per_y1)):
        unit_title = y1_unit.get("title", "?")
        logger.info("Judging unit %d/%d: %s", i + 1, total, unit_title[:60])
        if progress_callback:
            progress_callback(i + 1, total, unit_title)

        # Filter candidates to those with at least minimal similarity. The cut has
        # to track the embedding backend -- TF-IDF and mpnet cosines are not on the
        # same scale, and a mpnet-calibrated cut starves the judge of candidates on
        # the TF-IDF path, steering it toward REMOVED.
        from unsaid.aligner import get_thresholds
        candidate_cut = get_thresholds()["candidate"]
        strong_candidates = [(u, s) for u, s in candidates if s >= candidate_cut]
        result = judge_unit(
            y1_unit,
            strong_candidates,
            year1,
            year2,
            provider=provider,
            model=model,
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            azure_api_version=azure_api_version,
        )
        results.append(result)

        # Abort early rather than cache a run where the judge is mostly failing.
        failed = sum(1 for r in results if r.get("judge_failed"))
        if len(results) >= MIN_UNITS_BEFORE_RATE_CHECK:
            rate = failed / len(results)
            if rate > MAX_FALLBACK_RATE:
                raise JudgeFailureRateExceeded(
                    f"{failed}/{len(results)} judge calls failed ({rate:.0%}, limit "
                    f"{MAX_FALLBACK_RATE:.0%}) via {provider}/{model or 'default'}. "
                    f"Last error: {results[-1].get('judge_error', 'n/a')}. "
                    f"Refusing to write a result that would look like a valid analysis."
                )

    for y2_unit in new_candidates:
        results.append(judge_new_unit(y2_unit, year2))

    total_failed = sum(1 for r in results if r.get("judge_failed"))
    if total_failed:
        logger.warning(
            "%d/%d judge calls fell back to RETAINED; these carry confidence=0.0.",
            total_failed, len(results),
        )

    return results

