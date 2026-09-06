from apps.models.article import Article
from apps.models.chunk import ArticleChunk
from apps.rag.prompts import build_rag_prompt
from apps.rag.retrieval import RetrievedChunk


def _retrieved(title: str, url: str, content: str, score: float) -> RetrievedChunk:
    article = Article(title=title, url=url)
    chunk = ArticleChunk(content=content)
    return RetrievedChunk(chunk=chunk, article=article, score=score)


def test_build_rag_prompt_numbers_citations_in_order():
    retrieved = [
        _retrieved("Video A", "https://example.com/a", "content A", 0.9),
        _retrieved("Video B", "https://example.com/b", "content B", 0.8),
    ]
    prompt = build_rag_prompt("What is X?", retrieved)

    assert "[1] Video A (https://example.com/a)" in prompt
    assert "[2] Video B (https://example.com/b)" in prompt
    assert "content A" in prompt
    assert "content B" in prompt
    assert "What is X?" in prompt


def test_build_rag_prompt_includes_instruction_to_cite_and_say_when_unknown():
    prompt = build_rag_prompt("q", [_retrieved("T", "https://x.com", "c", 0.5)])
    assert "استشهد بالمصادر" in prompt
    assert "لا تعرف" in prompt
