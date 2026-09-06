from apps.rag.chunking import build_chunk_source_text, chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_single_chunk():
    chunks = chunk_text("A short sentence.", chunk_size=1000, overlap=150)
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].text == "A short sentence."


def test_long_text_splits_into_multiple_chunks_with_overlap():
    # 250 chars of repeating words so we can reason about boundaries.
    text = " ".join(f"word{i}" for i in range(60))  # well over 100 chars
    chunks = chunk_text(text, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    # indices are sequential starting at 0
    assert [c.index for c in chunks] == list(range(len(chunks)))
    # consecutive chunks overlap: some trailing words of one chunk reappear
    # at the start of the next (since we split on whitespace boundaries).
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert set(first_words) & set(second_words)


def test_does_not_split_mid_word_when_a_boundary_exists():
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    for chunk in chunks:
        for word in chunk.text.split():
            assert word in text.split()  # every emitted word is a real whole word


def test_overlap_must_be_smaller_than_chunk_size():
    import pytest

    with pytest.raises(ValueError):
        chunk_text("some text here", chunk_size=10, overlap=10)


def test_build_chunk_source_text_prefers_content_then_summary_then_title():
    assert build_chunk_source_text("Title", "Full content", "Summary") == "Title\n\nFull content"
    assert build_chunk_source_text("Title", None, "Summary") == "Title\n\nSummary"
    assert build_chunk_source_text("Title", None, None) == "Title"
