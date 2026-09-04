"""
Section extraction for 10-K filings.
Pulls Item 1A (Risk Factors) and Item 7A (Market Risk) as clean prose text.
"""
import re
import logging
from typing import Optional, Dict
from bs4 import BeautifulSoup

from unsaid.fetcher import edgar_call
from unsaid import textcache

logger = logging.getLogger(__name__)

_EXTRACTOR_FP = None

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


# Item 1A in a bank 10-K typically runs tens of thousands of characters. A
# table-of-contents entry slices to a few hundred, so a floor here separates the
# body from the index without needing to parse the TOC.
# Upper bound on a plausible section, from the observed distribution across 245
# cached filings: Item 1A runs p90=129k with five filings above 200k; Item 7A runs
# p90=56k with twelve above 200k. Set generously so a genuinely large section --
# Citigroup's Item 7A is 123k chars -- still passes, and only the clear
# over-captures are rejected.
_MAX_PLAUSIBLE_CHARS = {"1A": 250_000, "7A": 200_000}

# Lower bound, per section, and deliberately NOT symmetric.
#
# Item 1A is Risk Factors and is never legitimately short. Measured across 401
# cached filings its lengths form two populations with an empty band between
# them: 27 extractions at or below 2,181 chars (cross-reference pointers -- BK
# 9 words, USB 17, WFC 20) and 374 at or above 18,696 chars (real sections). The
# floor sits in that gap.
#
# Item 7A keeps the permissive floor on purpose. Two thirds of the universe
# route market risk into MD&A and leave a ~250-char pointer, so for 7A a short
# extraction is usually the CORRECT answer and must not be treated as failure.
_MIN_PLAUSIBLE_CHARS = {"1A": 8_000}

# Item 1A is often satisfied by a pointer to Exhibit 13, the Annual Report to
# Shareholders, where the Risk Factors prose actually lives.
_INCORP_BY_REF = re.compile(
    r"incorporat\w+\s+(?:herein\s+|in\w*\s+th\w+\s+[\w\s]{0,24}?)?by\s+reference", re.I)

# Inside the exhibit there are no "Item 1A" anchors to slice on, so the section
# is located by its heading PLUS the investor-facing preamble that follows it.
# The heading alone is not enough: "Risk Factors" appears up to 53 times in one
# exhibit, nearly all of them table-of-contents rows or cross-references.
_AR_OPENER = re.compile(
    r"\b(?:an\s+investment\s+in|investing\s+in|you\s+should\s+carefully\s+consider|"
    r"the\s+following\s+(?:discussion|risk)|our\s+business\s+is\s+subject\s+to|"
    r"we\s+are\s+subject\s+to\s+(?:a\s+number\s+of\s+)?risks)", re.I)
_AR_OPENER_WINDOW = 220

# Headings that follow Risk Factors in an annual report.
_AR_ENDERS = (
    "Report of Independent Registered Public Accounting Firm",
    "Consolidated Statement of Income",
    "Consolidated Balance Sheet",
    "Controls and Procedures",
    "Glossary of Acronyms",
    "Directors and Executive Officers",
    "Managing Committee",
)

# Titles of the items that can follow each section. Used to cut an over-capture
# back to its real end. Matched anchored to a whole line, because that is what
# distinguishes a heading from the same words used in a sentence: "cybersecurity
# incidents" and "residential properties" both occur inside Morgan Stanley's own
# risk prose and defeat unanchored matching.
_FOLLOWING_TITLES = {
    "1A": ("Unresolved Staff Comments", "Cybersecurity", "Properties",
           "Legal Proceedings", "Mine Safety Disclosures"),
    "7A": ("Financial Statements and Supplementary Data",
           "Changes in and Disagreements with Accountants",
           "Controls and Procedures"),
}

_MIN_SECTION_PROSE = 2_000
# Absolute floor, used only when nothing better is available.
_MIN_FALLBACK_PROSE = 200
# Hard cap on how far a section may extend when no end marker is found.
_MAX_SECTION_CHARS = 350_000
# How far to SEARCH for the end marker. Deliberately much larger than the cap:
# Citigroup's Item 7A body runs past 350k, and limiting the search to the cap
# makes a genuinely bounded section look unbounded and silently truncates it.
_END_SEARCH_WINDOW = 1_500_000
# Skip this much past the heading before looking for the end marker, so the
# heading's own neighbours do not terminate it immediately.
_END_SEARCH_OFFSET = 1_000

_SECTION_HTML_PATTERNS = {
    "1A": {
        "start": r'(?:<[^>]+>\s*(?:Item\s*1A[\.:\s\-\u2014\u2013]*|1A\.[\s&#;0-9a-z]*Risk\s+Factors|RISK\s+FACTORS)\s*<)',
        "end": r'(?:<[^>]+>\s*(?:Item\s*(?:1B|2|7A)[\.:\s\-\u2014\u2013]*|UNRESOLVED\s+STAFF\s+COMMENTS|PROPERTIES|MANAGING\s+GLOBAL\s+RISK)\s*<)',
    },
    "7A": {
        "start": r'(?:<[^>]+>\s*(?:Item\s*7A[\.:\s\-\u2014\u2013]*|7A\.[\s&#;0-9a-z]*Quantitative|MANAGING\s+GLOBAL\s+RISK|MARKET\s+RISK)\s*<)',
        "end": r'(?:<[^>]+>\s*(?:Item\s*8[\.:\s\-\u2014\u2013]*|FINANCIAL\s+STATEMENTS|CONSOLIDATED\s+FINANCIAL\s+STATEMENTS)\s*<)',
    },
}


def _slice_candidate(raw_html: str, start_idx: int, end_pattern: str):
    """
    Return (prose, bounded) for the section beginning at start_idx.

    bounded is True when a genuine end marker was found. An unbounded slice is
    almost always a cross-reference rather than the section itself, so callers
    should prefer a bounded candidate even if it appears earlier in the document.
    """
    window = raw_html[start_idx + _END_SEARCH_OFFSET : start_idx + _END_SEARCH_WINDOW]
    m_end = re.search(end_pattern, window, re.I)
    if m_end:
        end_idx = start_idx + _END_SEARCH_OFFSET + m_end.start()
        bounded = True
    else:
        end_idx = start_idx + _MAX_SECTION_CHARS
        bounded = False
    return _html_to_prose(raw_html[start_idx:end_idx]), bounded


def _extract_via_html_slice(raw_html: str, section: str) -> Optional[str]:
    """
    Locate a section by slicing raw HTML between heading boundaries.

    Resilient to filings whose table of contents lacks anchor tags (Citigroup
    styles Item 1A as a bare bold div and files Item 7A under MANAGING GLOBAL
    RISK), which is why the patterns admit heading text as well as item numbers.
    """
    if not raw_html or len(raw_html) < 500:
        return None

    pattern = _SECTION_HTML_PATTERNS.get(section)
    if not pattern:
        return None

    starts = list(re.finditer(pattern["start"], raw_html, re.I))
    if not starts:
        return None

    # Later headings are more likely to be the body than the table of contents,
    # so search backwards -- but require the slice to be bounded and substantial
    # rather than trusting position alone.
    best_unbounded = None
    for m in reversed(starts):
        prose, bounded = _slice_candidate(raw_html, m.start(), pattern["end"])
        if bounded and len(prose) >= _MIN_SECTION_PROSE:
            logger.info(
                "Extracted Item %s via HTML slice (bounded, len=%d, candidate %d/%d)",
                section, len(prose), starts.index(m) + 1, len(starts),
            )
            return prose
        if not bounded and best_unbounded is None and len(prose) >= _MIN_SECTION_PROSE:
            best_unbounded = prose

    # Nothing bounded. An unbounded slice is capped at _MAX_SECTION_CHARS and may
    # carry unrelated trailing content, so accept it only as a last resort and
    # say so, rather than letting it pass as a clean extraction.
    if best_unbounded:
        logger.warning(
            "Item %s HTML slice found no end marker; using a capped unbounded slice "
            "(len=%d). Content may extend beyond the section.",
            section, len(best_unbounded),
        )
        return best_unbounded

    for m in reversed(starts):
        prose, _ = _slice_candidate(raw_html, m.start(), pattern["end"])
        if len(prose) >= _MIN_FALLBACK_PROSE:
            logger.warning(
                "Item %s HTML slice produced only a short section (len=%d); "
                "this may be a table-of-contents entry rather than the body.",
                section, len(prose),
            )
            return prose

    return None


def _is_plausible(text: Optional[str], section: str) -> bool:
    """
    Whether an extraction is a credible instance of this section.

    Both bounds are per-section, because the two sections fail in opposite
    directions. Item 1A is Risk Factors: it is never legitimately short, so a
    short result means the extractor returned a cross-reference pointer instead
    of the section. Item 7A is the reverse -- two thirds of banks route market
    risk into MD&A and leave a ~250-char pointer, so a short Item 7A is usually
    the CORRECT answer and must not be treated as failure.
    """
    if not text:
        return False
    n = len(text)
    if n <= _MIN_PLAUSIBLE_CHARS.get(section, _MIN_FALLBACK_PROSE):
        return False
    return n <= _MAX_PLAUSIBLE_CHARS.get(section, 250_000)


def _truncate_over_capture(text: Optional[str], section: str) -> Optional[str]:
    """
    Cut a section that ran past its end back to the next item heading.

    Returns None when no heading is found, so the caller falls through rather
    than accepting an arbitrary truncation.
    """
    titles = _FOLLOWING_TITLES.get(section)
    if not text or not titles:
        return None
    floor = _MIN_PLAUSIBLE_CHARS.get(section, _MIN_FALLBACK_PROSE)
    cut = None
    for title in titles:
        for m in re.finditer(r"(?m)^\s*" + re.escape(title) + r"\s*$", text):
            # Below the floor it is a heading inside the section's own prose,
            # not the section's end.
            if m.start() >= floor and (cut is None or m.start() < cut):
                cut = m.start()
    return text[:cut] if cut else None


def _slice_risk_factors_from_prose(prose: str) -> Optional[str]:
    """
    Bound the Risk Factors section inside annual-report-style prose.

    Start is the first "Risk Factors" whose following text opens like a real
    section rather than a reference to one. End is the nearest following heading
    that leaves a plausible section behind -- the length check matters, because
    Wells Fargo cites "Consolidated Balance Sheet" 3,278 chars into its own risk
    prose, which is a mention and not the next heading.
    """
    if not prose:
        return None
    starts = [m.start() for m in re.finditer(r"Risk\s+Factors", prose, re.I)
              if _AR_OPENER.search(prose[m.end():m.end() + _AR_OPENER_WINDOW])]
    if not starts:
        return None
    start = starts[0]
    floor = _MIN_PLAUSIBLE_CHARS.get("1A", _MIN_FALLBACK_PROSE)

    end = None
    for pat in _AR_ENDERS:
        m = re.search(re.escape(pat), prose[start:], re.I)
        if m and m.start() >= floor and (end is None or m.start() < end):
            end = m.start()
    if end is None:
        logger.warning(
            "Risk Factors found in the annual report exhibit but no end heading "
            "followed it; capping at %d chars.", _MAX_SECTION_CHARS)
        return prose[start:start + _MAX_SECTION_CHARS]
    return prose[start:start + end]


def _extract_from_annual_report_exhibit(filing, section: str) -> Optional[str]:
    """
    Follow an incorporation-by-reference pointer into Exhibit 13.

    Only meaningful for Item 1A. Item 7A is not recovered this way: the two
    thirds of banks with no standalone 7A cross-reference into their own MD&A,
    not into a separate exhibit, so there is nothing to follow.
    """
    if section != "1A":
        return None
    try:
        attachments = edgar_call(lambda: filing.attachments)
    except Exception as e:
        logger.debug("Could not list attachments: %s", e)
        return None

    exhibit = None
    for att in attachments or []:
        try:
            kind = str(getattr(att, "document_type", "") or getattr(att, "type", "") or "")
        except Exception:
            continue
        if kind.upper().startswith("EX-13"):
            exhibit = att
            break
    if exhibit is None:
        return None

    html = None
    for meth in ("download", "content", "text"):
        try:
            attr = getattr(exhibit, meth, None)
            if attr is None:
                continue
            html = edgar_call(attr) if callable(attr) else attr
            if html:
                break
        except Exception:
            continue
    if not html:
        return None
    if isinstance(html, bytes):
        html = html.decode("utf-8", "ignore")

    body = _slice_risk_factors_from_prose(_html_to_prose(html))
    if body:
        logger.info(
            "Extracted Item %s from the Annual Report exhibit (EX-13) that Item %s "
            "incorporates by reference (len=%d)", section, section, len(body))
    return body


def extract_section(filing, section: str) -> Optional[str]:
    """
    Extract Item 1A or Item 7A from an edgartools Filing object.
    Returns clean prose text, or None if not found.
    """
    section = section.upper()

    # --- Attempt 1: edgartools TenK object native item access ---
    try:
        tenk = edgar_call(filing.obj)

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
            if _is_plausible(text, section):
                logger.info("Extracted Item %s via edgartools (len=%d)", section, len(text))
                return text
            if text:
                lo = _MIN_PLAUSIBLE_CHARS.get(section, _MIN_FALLBACK_PROSE)
                hi = _MAX_PLAUSIBLE_CHARS.get(section, 250_000)
                if len(text) > hi:
                    logger.warning(
                        "Rejected Item %s from edgartools: %d chars exceeds the plausible "
                        "maximum of %d, so the section boundary has overshot.",
                        section, len(text), hi,
                    )
                    # The START is usually right even when the end is not, so try
                    # cutting back to the next item heading before falling through.
                    trimmed = _truncate_over_capture(text, section)
                    if _is_plausible(trimmed, section):
                        logger.info(
                            "Recovered Item %s by truncating the over-capture at the next "
                            "item heading (%d -> %d chars)", section, len(text), len(trimmed))
                        return trimmed
                elif len(text) <= lo:
                    logger.warning(
                        "Rejected Item %s from edgartools: %d chars is below the plausible "
                        "minimum of %d, so this is a cross-reference pointer rather than "
                        "the section.", section, len(text), lo,
                    )
                    # If the pointer says the section is incorporated by reference,
                    # take the filing at its word: the primary document does not
                    # contain the section, and the later attempts search only the
                    # primary document. They cannot find it, but they CAN return a
                    # plausibly-sized slice of whatever follows -- which no size
                    # gate can catch. Go straight to the exhibit instead.
                    if _INCORP_BY_REF.search(text):
                        logger.info(
                            "Item %s is incorporated by reference; following it to the "
                            "Annual Report exhibit rather than searching the primary "
                            "document.", section,
                        )
                        body = _extract_from_annual_report_exhibit(filing, section)
                        if _is_plausible(body, section):
                            return body
                        if body:
                            logger.warning(
                                "Rejected Item %s from the annual report exhibit: %d "
                                "chars is outside the plausible range.", section, len(body),
                            )
    except Exception as e:
        logger.debug("edgartools native extraction failed for Item %s: %s", section, e)

    # --- Attempt 2: direct HTML boundary slice fallback ---
    try:
        if hasattr(filing, "html"):
            raw_html = edgar_call(filing.html)
            if raw_html:
                res = _extract_via_html_slice(raw_html, section)
                if _is_plausible(res, section):
                    logger.info("Extracted Item %s via HTML boundary slice fallback (len=%d)", section, len(res))
                    return res
                if res:
                    logger.warning(
                        "Rejected Item %s from HTML slice: %d chars is outside the "
                        "plausible range.", section, len(res),
                    )
    except Exception as e:
        logger.debug("HTML slice fallback failed for Item %s: %s", section, e)

    # --- Attempt 3: regex scan over full text document ---
    try:
        full_text = getattr(filing, "_cached_full_text", None)
        if not full_text:
            if hasattr(filing, "text"):
                try:
                    full_text = edgar_call(filing.text)
                except Exception:
                    pass
            if not full_text and hasattr(filing, "markdown"):
                try:
                    full_text = edgar_call(filing.markdown)
                except Exception:
                    pass
            if full_text:
                try:
                    setattr(filing, "_cached_full_text", full_text)
                except Exception:
                    pass

        if full_text:
            result = _extract_via_regex(full_text, section)
            if _is_plausible(result, section):
                logger.info("Extracted Item %s via regex fallback (len=%d)", section, len(result))
                return result
            if result:
                logger.warning(
                    "Rejected Item %s from regex fallback: %d chars is outside the "
                    "plausible range.", section, len(result),
                )
    except Exception as e:
        logger.debug("Regex fallback failed for Item %s: %s", section, e)

    # --- Attempt 4: follow incorporation by reference into Exhibit 13 ---
    # Deliberately last: it downloads a second, often very large document, so it
    # runs only when the primary document genuinely has not yielded the section.
    try:
        body = _extract_from_annual_report_exhibit(filing, section)
        if _is_plausible(body, section):
            return body
        if body:
            logger.warning(
                "Rejected Item %s from the annual report exhibit: %d chars is outside "
                "the plausible range.", section, len(body),
            )
    except Exception as e:
        logger.debug("Annual report exhibit fallback failed for Item %s: %s", section, e)

    logger.warning(
        "Could not extract a plausible Item %s from filing; every attempt was empty "
        "or outside the plausible size range. Returning None rather than a section "
        "that is not the section.", section,
    )
    return None


def _extractor_fingerprint() -> str:
    """
    Identity of the extraction logic, used to key the text cache.

    Derived from this module's own source so that editing any extraction rule
    invalidates cached text automatically. Without it a corpus could silently mix
    output from two different extractors -- the exact defect that made the
    banking study's cohorts incomparable.
    """
    global _EXTRACTOR_FP
    if _EXTRACTOR_FP is None:
        import hashlib
        from pathlib import Path
        # Normalise line endings before hashing. Git rewrites tracked files
        # with CRLF on Windows checkout, so hashing raw bytes makes the
        # fingerprint depend on the platform and on which branch was last
        # checked out. That silently invalidates the entire text cache and
        # starts a multi-hour re-extraction with no code change behind it.
        src = Path(__file__).resolve().read_bytes().replace(b"\r\n", b"\n")
        _EXTRACTOR_FP = hashlib.sha256(src).hexdigest()[:10]
    return _EXTRACTOR_FP


def extract_both_sections(filing, use_cache: bool = True) -> Dict[str, Optional[str]]:
    """
    Extract Item 1A and Item 7A, reusing cached text where available.

    Every filing appears twice in a corpus of consecutive year-pairs (as Year-2
    of one and Year-1 of the next), so caching by accession removes half the
    extraction work outright.
    """
    accession = str(getattr(filing, "accession_no", "") or "")

    if use_cache and accession:
        fp = _extractor_fingerprint()
        cached = textcache.load(accession, fp)
        if cached is not None:
            logger.info(
                "Text cache hit for %s (1A=%d chars, 7A=%d chars)",
                accession,
                len(cached.get("1A") or ""),
                len(cached.get("7A") or ""),
            )
            return {"1A": cached.get("1A"), "7A": cached.get("7A")}

    sections = {
        "1A": extract_section(filing, "1A"),
        "7A": extract_section(filing, "7A"),
    }

    # Only cache a filing where something was actually recovered; caching a total
    # failure would make a transient fetch error permanent.
    if use_cache and accession and any(sections.values()):
        textcache.store(accession, _extractor_fingerprint(), sections)

    return sections
