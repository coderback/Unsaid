"""
Embedding-based alignment of Year-1 vs Year-2 disclosure units.
Embeddings are used ONLY for candidate recall — Claude judges every classification.
Model: all-mpnet-base-v2 (local, no API key).
"""
import logging
from typing import List, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_EMBED_MODEL = None
_MODEL_NAME = "all-mpnet-base-v2"

# Top-K candidates sent to the judge per Year-1 unit
K = 5
# Threshold below which a Year-2 unit is considered "orphaned" (candidate for NEW)
NEW_THRESHOLD = 0.30
# Threshold below which we pass NO strong candidates → judge sees empty list → likely REMOVED
WEAK_MATCH_THRESHOLD = 0.30


def _get_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model %s …", _MODEL_NAME)
        _EMBED_MODEL = SentenceTransformer(_MODEL_NAME)
        logger.info("Model loaded.")
    return _EMBED_MODEL


def embed_units(units: List[Dict]) -> np.ndarray:
    """Embed a list of disclosure units; returns float32 array shape (n, dim), L2-normalised."""
    model = _get_model()
    texts = [u.get("text", "") for u in units]
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 20,
        batch_size=32,
    )
    return embeddings.astype(np.float32)


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
    y1_embs = embed_units(y1_units)
    y2_embs = embed_units(y2_units)

    # Cosine similarity matrix (normalised vectors → dot product = cosine sim)
    sim_matrix = y1_embs @ y2_embs.T  # shape (n1, n2)

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
    new_candidates = [
        y2_units[j]
        for j in range(len(y2_units))
        if max_sim_per_y2[j] < NEW_THRESHOLD
    ]
    logger.info(
        "Alignment complete. %d Year-2 units flagged as potential NEW.",
        len(new_candidates)
    )

    return candidates_per_y1, new_candidates
