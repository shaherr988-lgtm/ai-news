from datetime import datetime, timezone
from unittest.mock import MagicMock

from apps.pipeline.call_budget import CallBudget
from apps.pipeline.curate import select_most_important
from apps.pipeline.fetched_item import FetchedItem


def _item(n: int) -> FetchedItem:
    return FetchedItem(
        external_id=f"id{n}",
        title=f"Title {n}",
        url=f"https://example.com/{n}",
        content=f"content {n}",
        published_at=datetime.now(timezone.utc),
    )


def test_returns_all_items_unchanged_when_under_the_limit():
    provider = MagicMock()
    items = [_item(i) for i in range(5)]

    result = select_most_important(provider, items, keep=10)

    assert result == items
    provider.generate.assert_not_called()


def test_selects_items_by_parsed_indices_in_order():
    provider = MagicMock()
    provider.generate.return_value = "3, 1"
    items = [_item(i) for i in range(1, 4)]  # 3 items, keep 2

    result = select_most_important(provider, items, keep=2)

    assert [item.title for item in result] == ["Title 3", "Title 1"]


def test_falls_back_to_feed_order_when_response_has_no_numbers():
    provider = MagicMock()
    provider.generate.return_value = "ما قدرت أحدد، كلها مهمة"
    items = [_item(i) for i in range(1, 6)]

    result = select_most_important(provider, items, keep=2)

    assert [item.title for item in result] == ["Title 1", "Title 2"]


def test_falls_back_to_feed_order_when_provider_raises():
    provider = MagicMock()
    provider.generate.side_effect = RuntimeError("boom")
    items = [_item(i) for i in range(1, 6)]

    result = select_most_important(provider, items, keep=2)

    assert [item.title for item in result] == ["Title 1", "Title 2"]


def test_ignores_out_of_range_and_duplicate_indices():
    provider = MagicMock()
    provider.generate.return_value = "99, 2, 2, 1"
    items = [_item(i) for i in range(1, 4)]

    result = select_most_important(provider, items, keep=2)

    assert [item.title for item in result] == ["Title 2", "Title 1"]


def test_skips_llm_call_when_budget_is_exhausted():
    provider = MagicMock()
    items = [_item(i) for i in range(1, 6)]
    budget = CallBudget(total=0)

    result = select_most_important(provider, items, keep=2, budget=budget)

    assert [item.title for item in result] == ["Title 1", "Title 2"]
    provider.generate.assert_not_called()
