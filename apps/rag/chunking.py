"""Splitting raw article/video text into overlapping, retrievable chunks
before embedding. Pure functions — no I/O, no DB, no network — easy to test.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    text: str


def chunk_text(text: str, *, chunk_size: int = 1000, overlap: int = 150) -> list[Chunk]:
    """Split `text` into overlapping chunks, operating on whole words so a
    word is never split across two chunks (chunk_size/overlap are soft
    per-chunk character targets, not hard byte offsets — a single word
    longer than chunk_size is kept whole rather than mangled).

    Returns [] for empty/whitespace-only input.
    """
    text = (text or "").strip()
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    index = 0
    start_word = 0
    n = len(words)

    while start_word < n:
        current: list[str] = []
        current_len = 0
        i = start_word
        while i < n:
            extra = len(words[i]) + (1 if current else 0)  # +1 for the joining space
            if current and current_len + extra > chunk_size:
                break
            current.append(words[i])
            current_len += extra
            i += 1

        if not current:
            # A single word longer than chunk_size — keep it whole rather
            # than cut it; better an oversized chunk than a mangled word.
            current = [words[i]]
            i += 1

        chunks.append(Chunk(index=index, text=" ".join(current)))
        index += 1

        if i >= n:
            break

        # Back off by whole words to build the overlap, then always make
        # forward progress (at least one new word next chunk).
        overlap_chars = 0
        overlap_words = 0
        j = i - 1
        while j >= start_word and overlap_chars < overlap:
            overlap_chars += len(words[j]) + 1
            overlap_words += 1
            j -= 1
        start_word = max(i - overlap_words, start_word + 1)

    return chunks


def build_chunk_source_text(title: str, content: str | None, summary: str | None) -> str:
    """What to chunk for an Article: prefer full content, fall back to the
    LLM summary, then the title alone — mirrors the fallback chain already
    used by prompts.build_item_summary_prompt for consistency."""
    body = content or summary or ""
    return f"{title}\n\n{body}".strip()
