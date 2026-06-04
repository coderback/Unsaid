"""
Section extraction for 10-K filings.
Pulls Item 1A (Risk Factors) and Item 7A (Market Risk) as clean prose text.
"""
import re
import logging
from typing import Optional, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Lines that are pure table garbage (mostly numbers / symbols, no real prose)
_GARBAGE_LINE = re.compile(r"^[\s\d\$\%\.\,\(\)\-\|\—\–\*\/\\n]+$")
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")

# Section header patterns used as fallback when edgartools can't find the section
_ITEM_1A_RE = re.compile(r"^\s*item\s+1a[\.\s:;—–\-]*", re.IGNORECASE | re.MULTILINE)
_ITEM_7A_RE = re.compile(r"^\s*item\s+7a[\.\s:;—–\-]*", re.IGNORECASE | re.MULTILINE)
_ITEM_8_RE  = re.compile(r"^\s*item\s+8[\.\s:;—–\-]*",  re.IGNORECASE | re.MULTILINE)
_ITEM_2_RE  = re.compile(r"^\s*item\s+2[\.\s:;—–\-]*",  re.IGNORECASE | re.MULTILINE)


def _html_to_prose(html_or_text: str) -> str:
    """
    Convert HTML (or already-plain text) to clean prose.
    Preserves inline quantitative statements (the EVE numbers matter).
    Strips table rows that are purely numeric/formatting noise.
    """
    if not html_or_text:
        return ""

    raw = str(html_or_text)

    # If it looks like HTML, parse it; otherwise treat as plain text
    if "<" in raw and ">" in raw:
        soup = BeautifulSoup(raw, "lxml")

        # For tables: keep rows that have meaningful prose cells,
        # drop rows that are all numbers / formatting symbols
        for table in soup.find_all("table"):
            kept_rows: list[str] = []
            for row in table.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
                cells = [c for c in cells if c]
                if not cells:
                    continue
                # A "prose" cell has more than 4 non-numeric characters
                has_prose = any(
                    len(re.sub(r"[\d\$\%\.\,\(\)\-\|\s]", "", c)) > 4
                    for c in cells
                )
                if has_prose:
                    kept_rows.append(" | ".join(cells))
            table.replace_with("\n".join(kept_rows) + "\n" if kept_rows else "")

        text = soup.get_text(separator="\n")
    else:
        text = raw

    # Filter line-by-line
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not _GARBAGE_LINE.match(stripped):
            lines.append(stripped)

    text = "\n".join(lines)
    text = _MULTIPLE_NEWLINES.sub("\n\n", text)
    text = _MULTIPLE_SPACES.sub(" ", text)
    return text.strip()


def _slice_between(text: str, start_re: re.Pattern, end_re: re.Pattern) -> Optional[str]:
    """Return the substring of `text` between the first match of start_re and end_re."""
    m_start = start_re.search(text)
    if not m_start:
        return None
    rest = text[m_start.start():]
    m_end = end_re.search(rest)
    if m_end and m_end.start() > 100:
        return rest[: m_end.start()].strip()
    return rest.strip() or None


def _extract_via_regex(full_text: str, section: str) -> Optional[str]:
    """Fallback: find section in plain text by regex."""
    if section == "1A":
        return _slice_between(full_text, _ITEM_1A_RE, _ITEM_2_RE)
    elif section == "7A":
        return _slice_between(full_text, _ITEM_7A_RE, _ITEM_8_RE)
    return None


def extract_section(filing, section: str) -> Optional[str]:
    """
    Extract Item 1A or Item 7A from an edgartools Filing object.
    Returns clean prose text, or None if not found.
    """
    section = section.upper()

    # --- Attempt 1: edgartools TenK object native item access ---
    try:
        tenk = filing.obj()

        # Try multiple access patterns that edgartools supports
        keys_to_try = {
            "1A": ["Item 1A", "item1a", "risk_factors", "1A"],
            "7A": ["Item 7A", "item7a", "market_risk", "7A"],
        }[section]

        raw = None
        for key in keys_to_try:
            try:
                val = tenk[key] if hasattr(tenk, "__getitem__") else getattr(tenk, key, None)
                if val:
                    raw = val
                    break
            except (KeyError, TypeError, AttributeError):
                pass
            # Also try attribute access
            attr = key.replace(" ", "").lower()
            val = getattr(tenk, attr, None)
            if val:
                raw = val
                break

        if raw:
            text = _html_to_prose(str(raw))
            if len(text) > 200:
                logger.info("Extracted Item %s via edgartools (len=%d)", section, len(text))
                return text
    except Exception as e:
        logger.debug("edgartools native extraction failed for Item %s: %s", section, e)

    # --- Attempt 2: regex scan over full filing document ---
    try:
        tenk = filing.obj()
        full_raw = str(tenk)
        full_text = _html_to_prose(full_raw)
        result = _extract_via_regex(full_text, section)
        if result and len(result) > 200:
            logger.info("Extracted Item %s via regex fallback (len=%d)", section, len(result))
            return result
    except Exception as e:
        logger.debug("Regex fallback failed for Item %s: %s", section, e)

    logger.warning("Could not extract Item %s from filing", section)
    return None


def extract_both_sections(filing) -> Dict[str, Optional[str]]:
    """Extract both Item 1A and Item 7A from a filing."""
    return {
        "1A": extract_section(filing, "1A"),
        "7A": extract_section(filing, "7A"),
    }
