from unittest.mock import MagicMock

from apps.agent.fallback_provider import FallbackLLMProvider


def test_summarize_uses_primary_when_it_succeeds():
    primary = MagicMock(summarize=MagicMock(return_value="primary summary"))
    fallback = MagicMock(summarize=MagicMock(return_value="fallback summary"))
    provider = FallbackLLMProvider(primary, fallback)

    result = provider.summarize("system", "content", max_tokens=300)

    assert result == "primary summary"
    fallback.summarize.assert_not_called()


def test_summarize_falls_back_when_primary_raises():
    primary = MagicMock(summarize=MagicMock(side_effect=RuntimeError("rate limited")))
    fallback = MagicMock(summarize=MagicMock(return_value="fallback summary"))
    provider = FallbackLLMProvider(primary, fallback)

    result = provider.summarize("system", "content", max_tokens=300)

    assert result == "fallback summary"
    fallback.summarize.assert_called_once_with("system", "content", max_tokens=300)


def test_generate_uses_primary_when_it_succeeds():
    primary = MagicMock(generate=MagicMock(return_value="primary html"))
    fallback = MagicMock(generate=MagicMock(return_value="fallback html"))
    provider = FallbackLLMProvider(primary, fallback)

    result = provider.generate("system", "prompt", max_tokens=2000)

    assert result == "primary html"
    fallback.generate.assert_not_called()


def test_generate_falls_back_when_primary_raises():
    primary = MagicMock(generate=MagicMock(side_effect=RuntimeError("empty response")))
    fallback = MagicMock(generate=MagicMock(return_value="fallback html"))
    provider = FallbackLLMProvider(primary, fallback)

    result = provider.generate("system", "prompt", max_tokens=2000)

    assert result == "fallback html"
    fallback.generate.assert_called_once_with("system", "prompt", max_tokens=2000)


def test_generate_raises_when_both_fail():
    primary = MagicMock(generate=MagicMock(side_effect=RuntimeError("primary down")))
    fallback = MagicMock(generate=MagicMock(side_effect=RuntimeError("fallback down too")))
    provider = FallbackLLMProvider(primary, fallback)

    try:
        provider.generate("system", "prompt")
        assert False, "expected an exception"
    except RuntimeError as e:
        assert "fallback down too" in str(e)
