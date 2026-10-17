"""SQLite engine, session dependency, and table creation.

Run `python -m db` (or import `create_db_and_tables`) to create the tables.
"""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

import config

engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    """Create every table declared on SQLModel subclasses."""
    # Import for the side effect of registering the models on SQLModel.metadata.
    import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with Session(engine) as session:
        yield session


if __name__ == "__main__":
    create_db_and_tables()
    print(f"tables created in {config.DATABASE_URL}")
