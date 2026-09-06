"""Pure vector-similarity math. In production, the actual ranking happens
server-side via pgvector's cosine-distance operator (apps/rag/retrieval.py) —
this module exists so that ranking logic has direct, DB-free unit coverage.
"""

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"vector length mismatch: {len(a)} vs {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def top_k_by_similarity(
    query_vector: list[float], candidates: list[tuple[int, list[float]]], k: int
) -> list[tuple[int, float]]:
    """Given (id, vector) candidates, return the top-k ids by cosine
    similarity to query_vector, highest first."""
    scored = [(cid, cosine_similarity(query_vector, vec)) for cid, vec in candidates]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:k]
