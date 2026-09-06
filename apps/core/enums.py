import enum


class SourceType(str, enum.Enum):
    """The kind of source we ingest content from."""

    YOUTUBE = "youtube"
    BLOG = "blog"
    ARXIV = "arxiv"
