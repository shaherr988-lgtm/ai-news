"""One-off: enable the pgvector extension and create all tables in the
configured database.

Run with: python -m scripts.create_tables
"""

from sqlalchemy import text

from apps.core.db import create_all_tables, engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    create_all_tables()
    print("pgvector extension enabled and tables created (or already existed).")


if __name__ == "__main__":
    main()
