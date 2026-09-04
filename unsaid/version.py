"""
Pipeline fingerprint — identifies the exact code + model configuration that
produced a result.

The banking study was ingested over five days while seven pipeline commits
landed, and because each cohort happened to be processed on a different day, a
bank's unit yield depended partly on when it was run rather than on its filings.
Nothing in the output recorded which pipeline produced it, so the confound was
invisible until someone compared file timestamps against git log.

The fingerprint is a hash of the pipeline source plus the model configuration.
It is derived rather than hand-maintained: editing any pipeline module changes
it automatically, so a stale version string cannot silently claim two runs are
comparable when they are not.

This is deliberately conservative. A docstring edit changes the fingerprint even
though it cannot change output. For a research instrument, over-invalidating is
the correct failure mode -- a spurious re-ingest costs compute, while a missed
one silently corrupts a cross-section.
"""
import hashlib
from pathlib import Path
from typing import Optional

_MODULE_DIR = Path(__file__).resolve().parent

# Excluded because they cannot affect what a run produces.
_EXCLUDED = {"version.py", "__init__.py"}


def code_fingerprint() -> str:
    """Hash of every pipeline module that can influence output."""
    h = hashlib.sha256()
    for path in sorted(_MODULE_DIR.glob("*.py")):
        if path.name in _EXCLUDED:
            continue
        h.update(path.name.encode("utf-8"))
        # LF-normalised so a Windows checkout cannot change the hash;
        # see the note in extractor.py._extractor_fingerprint.
        h.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def pipeline_fingerprint(
    provider: Optional[str] = None,
    model_judge: Optional[str] = None,
    model_segmenter: Optional[str] = None,
    embed_backend: Optional[str] = None,
) -> str:
    """
    Full fingerprint: pipeline code plus the model configuration.

    embed_backend matters as much as the models do -- dense mpnet and bag-of-words
    TF-IDF produce different candidate sets and are not interchangeable, so runs
    that differ only in backend must not be treated as comparable.
    """
    h = hashlib.sha256()
    h.update(code_fingerprint().encode("utf-8"))
    for part in (provider, model_judge, model_segmenter, embed_backend):
        h.update(b"\x00")
        h.update((part or "").encode("utf-8"))
    return h.hexdigest()[:12]


def describe(
    provider: Optional[str] = None,
    model_judge: Optional[str] = None,
    model_segmenter: Optional[str] = None,
    embed_backend: Optional[str] = None,
) -> dict:
    """Human-readable provenance block to store alongside results."""
    return {
        "pipeline_version": pipeline_fingerprint(
            provider, model_judge, model_segmenter, embed_backend
        ),
        "code_fingerprint": code_fingerprint(),
        "provider": provider,
        "model_judge": model_judge,
        "model_segmenter": model_segmenter,
        "embed_backend": embed_backend,
    }
