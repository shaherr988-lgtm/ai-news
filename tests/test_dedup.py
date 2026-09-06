from dataclasses import dataclass
from datetime import datetime, timezone

from apps.pipeline.dedup import filter_new_items


@dataclass
class FakeItem:
    external_id: str | None
    title: str
    url: str
    content: str | None = None
    published_at: datetime = datetime.now(timezone.utc)


def test_rejects_duplicate_by_external_id():
    items = [FakeItem(external_id="vid1", title="A", url="https://example.com/a")]
    new_items = filter_new_items(
        items, existing_external_ids={"vid1"}, existing_urls=set()
    )
    assert new_items == []


def test_rejects_duplicate_by_url_when_no_external_id():
    items = [FakeItem(external_id=None, title="A", url="https://example.com/a")]
    new_items = filter_new_items(
        items, existing_external_ids=set(), existing_urls={"https://example.com/a"}
    )
    assert new_items == []


def test_external_id_checked_before_url():
    # url is "new" but external_id matches an existing one -> still a duplicate.
    items = [FakeItem(external_id="vid1", title="A", url="https://example.com/new-url")]
    new_items = filter_new_items(
        items, existing_external_ids={"vid1"}, existing_urls=set()
    )
    assert new_items == []


def test_accepts_genuinely_new_item():
    items = [FakeItem(external_id="vid2", title="B", url="https://example.com/b")]
    new_items = filter_new_items(items, existing_external_ids={"vid1"}, existing_urls=set())
    assert len(new_items) == 1
    assert new_items[0].url == "https://example.com/b"


def test_dedupes_within_the_same_batch():
    items = [
        FakeItem(external_id="vid3", title="C", url="https://example.com/c"),
        FakeItem(external_id="vid3", title="C dup", url="https://example.com/c-dup"),
    ]
    new_items = filter_new_items(items, existing_external_ids=set(), existing_urls=set())
    assert len(new_items) == 1
