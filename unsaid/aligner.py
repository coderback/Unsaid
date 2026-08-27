"""
Embedding-based alignment of Year-1 vs Year-2 disclosure units.
Embeddings are used ONLY for candidate recall — Claude judges every classification.
Model: all-mpnet-base-v2 (local, no API key).
"""
import logging
import threading
from typing import List, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_EMBED_MODEL = None
_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
_FALLBACK_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Which backend actually produced the last alignment. The pipeline previously
# degraded from dense embeddings to bag-of-words TF-IDF without recording it
# anywhere, so cached analyses claimed mpnet regardless of what really ran.
_ACTIVE_BACKEND: str = "uninitialised"

# Serialises model loading (so concurrent workers do not each download and
# instantiate mpnet) and encoding (a single torch module shared across threads).
# Encoding is seconds against minutes of LLM latency, so serialising it costs
# almost nothing at the pair level.
_MODEL_LOCK = threading.Lock()
_ENCODE_LOCK = threading.Lock()

# TF-IDF cosine and mpnet cosine are not on the same scale, so the recall
# thresholds have to differ per backend. TF-IDF over long, highly repetitive
# disclosure prose runs high on near-duplicates and low on true paraphrases.
_THRESHOLDS = {
    "mpnet": {"new": 0.30, "candidate": 0.20},
    "minilm": {"new": 0.30, "candidate": 0.20},
    "tfidf": {"new": 0.12, "candidate": 0.08},
}


def get_active_backend() -> str:
    """Backend used by the most recent alignment: 'mpnet', 'minilm' or 'tfidf'."""
    return _ACTIVE_BACKEND


def get_thresholds() -> dict:
    """Recall thresholds calibrated for the active backend."""
    return _THRESHOLDS.get(_ACTIVE_BACKEND, _THRESHOLDS["mpnet"])

# Top-K candidates sent to the judge per Year-1 unit
K = 5
# Threshold below which a Year-2 unit is considered "orphaned" (candidate for NEW)
NEW_THRESHOLD = 0.30
# Threshold below which we pass NO strong candidates → judge sees empty list → likely REMOVED
WEAK_MATCH_THRESHOLD = 0.30


def _load_sentence_transformer(name: str):
    """
    Load a sentence-transformers model, working around a stale HuggingFace token.

    When a token is present but not valid for a repo, the hub answers 401 rather
    than 404 for optional files such as adapter_config.json, and transformers
    surfaces that as the misleading "is not a valid model identifier". Disabling
    the implicit token makes public models resolve anonymously.
    """
    import os

    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(name, token=False)
    except TypeError:
        # Older sentence-transformers versions do not accept `token`.
        return SentenceTransformer(name)


def _get_model():
    global _EMBED_MODEL, _ACTIVE_BACKEND
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL

    with _MODEL_LOCK:
        if _EMBED_MODEL is not None:  # another thread won the race
            return _EMBED_MODEL
        return _load_model_locked()


def _load_model_locked():
    global _EMBED_MODEL, _ACTIVE_BACKEND

    for name, backend in ((_MODEL_NAME, "mpnet"), (_FALLBACK_MODEL_NAME, "minilm")):
        try:
            logger.info("Loading sentence-transformers model %s …", name)
            _EMBED_MODEL = _load_sentence_transformer(name)
            _ACTIVE_BACKEND = backend
            logger.info("Dense embedding backend active: %s (%s)", backend, name)
            return _EMBED_MODEL
        except Exception as e:
            logger.warning("Could not load %s: %s: %s", name, type(e).__name__, e)

    # Degrading to bag-of-words changes what the pipeline measures. It is a
    # legitimate fallback but must never pass unnoticed, because every downstream
    # artifact otherwise claims dense semantic alignment.
    logger.error(
        "DENSE EMBEDDINGS UNAVAILABLE — falling back to TF-IDF bag-of-words alignment. "
        "This is NOT the documented all-mpnet-base-v2 path: recall quality and the "
        "meaning of similarity scores both change. Results will be tagged "
        "embed_backend='tfidf'. Install the model to restore dense alignment."
    )
    _EMBED_MODEL = "TFIDF_FALLBACK"
    _ACTIVE_BACKEND = "tfidf"
    return _EMBED_MODEL


def embed_units(units: List[Dict]) -> np.ndarray:
    """Embed a list of disclosure units; returns float32 array shape (n, dim), L2-normalised."""
    model = _get_model()
    texts = [u.get("text", "") for u in units]

    if model != "TFIDF_FALLBACK" and hasattr(model, "encode"):
        try:
            with _ENCODE_LOCK:
                embeddings = model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=len(texts) > 20,
                    batch_size=32,
                )
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.warning("SentenceTransformer encode failed (%s). Using local TF-IDF fallback.", e)

    # Local TF-IDF Fallback (Fast, offline, robust)
    from sklearn.feature_extraction.text import TfidfVectorizer
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=10000,
        sublinear_tf=True,
        norm="l2",
    )
    # Fit on all texts and transform
    matrix = vectorizer.fit_transform(texts if texts else [""])
    return matrix.toarray().astype(np.float32)



def align_units(
    y1_units: List[Dict],
    y2_units: List[Dict],
) -> Tuple[List[List[Tuple[Dict, float]]], List[Dict]]:
    """
    For each Year-1 unit, find the top-K most similar Year-2 units (by cosine similarity).
    Also identify Year-2 "orphan" units that have no strong Year-1 match → candidates for NEW.

    Returns:
        candidates_per_y1: list of length len(y1_units), each element is
                           [(y2_unit, similarity), ...] sorted descending
        new_candidates:    y2 units with max similarity to any y1 unit < NEW_THRESHOLD
    """
    if not y1_units or not y2_units:
        logger.warning("Empty unit list passed to align_units")
        return [[] for _ in y1_units], list(y2_units) if not y1_units else []

    logger.info(
        "Embedding %d Year-1 units and %d Year-2 units …",
        len(y1_units), len(y2_units)
    )
    y1_texts = [u.get("text", "") for u in y1_units]
    y2_texts = [u.get("text", "") for u in y2_units]

    model = _get_model()
    sim_matrix = None

    global _ACTIVE_BACKEND
    if model != "TFIDF_FALLBACK" and hasattr(model, "encode"):
        try:
            with _ENCODE_LOCK:
                y1_embs = model.encode(y1_texts, normalize_embeddings=True, batch_size=32).astype(np.float32)
                y2_embs = model.encode(y2_texts, normalize_embeddings=True, batch_size=32).astype(np.float32)
            sim_matrix = y1_embs @ y2_embs.T  # shape (n1, n2)
        except Exception as e:
            logger.error(
                "Dense encoding failed mid-run (%s); this alignment falls back to TF-IDF "
                "and will be tagged embed_backend='tfidf'.", e,
            )
            _ACTIVE_BACKEND = "tfidf"

    if sim_matrix is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=10000,
            sublinear_tf=True,
            norm="l2",
        )
        combined_matrix = vectorizer.fit_transform(y1_texts + y2_texts).toarray().astype(np.float32)
        y1_embs = combined_matrix[:len(y1_texts)]
        y2_embs = combined_matrix[len(y1_texts):]
        sim_matrix = y1_embs @ y2_embs.T

    # Top-K candidates for each Year-1 unit
    k_actual = min(K, len(y2_units))
    candidates_per_y1: List[List[Tuple[Dict, float]]] = []

    for i, y1_unit in enumerate(y1_units):
        sims = sim_matrix[i]
        top_k_idx = np.argsort(sims)[::-1][:k_actual]
        candidates = [
            (y2_units[int(j)], float(sims[j]))
            for j in top_k_idx
        ]
        candidates_per_y1.append(candidates)

        best_sim = float(sims[top_k_idx[0]]) if len(top_k_idx) > 0 else 0.0
        logger.debug(
            "Y1 unit '%s' best match sim=%.3f → '%s'",
            y1_unit.get("title", "?")[:50],
            best_sim,
            y2_units[int(top_k_idx[0])].get("title", "?")[:50] if len(top_k_idx) > 0 else "—",
        )

    # Identify Year-2 orphans (no strong match from any Year-1 unit)
    max_sim_per_y2 = sim_matrix.max(axis=0)  # shape (n2,)
    new_threshold = get_thresholds()["new"]
    new_candidates = [
        y2_units[j]
        for j in range(len(y2_units))
        if max_sim_per_y2[j] < new_threshold
    ]
    logger.info(
        "Alignment complete via %s (NEW threshold %.2f). %d Year-2 units flagged as potential NEW.",
        _ACTIVE_BACKEND, new_threshold, len(new_candidates),
    )

    return candidates_per_y1, new_candidates
