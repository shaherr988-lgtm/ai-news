import pytest

from apps.rag.similarity import cosine_similarity, top_k_by_similarity


def test_identical_vectors_have_similarity_one():
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)


def test_orthogonal_vectors_have_similarity_zero():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_opposite_vectors_have_similarity_negative_one():
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)


def test_zero_vector_returns_zero_instead_of_dividing_by_zero():
    assert cosine_similarity([0, 0], [1, 1]) == 0.0


def test_mismatched_length_raises():
    with pytest.raises(ValueError):
        cosine_similarity([1, 0], [1, 0, 0])


def test_top_k_by_similarity_orders_highest_first():
    query = [1, 0]
    candidates = [
        (1, [0, 1]),    # orthogonal -> 0.0
        (2, [1, 0]),    # identical -> 1.0
        (3, [-1, 0]),   # opposite -> -1.0
        (4, [0.9, 0.1]),  # close -> high but not 1.0
    ]
    ranked = top_k_by_similarity(query, candidates, k=2)
    assert [cid for cid, _score in ranked] == [2, 4]
