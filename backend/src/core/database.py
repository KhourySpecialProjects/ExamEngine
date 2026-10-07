from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
from src.core.relabel_blocks import relabel_block_times
from src.schemas.db import Base


# Get settings
settings = get_settings()

# Create engine with settings from configuration
engine = create_engine(
    settings.database_url,
    # Connection pooling settings from config
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    # Enable SQL logging in debug mode
    echo=settings.debug,
    # Verify connections before using them
    pool_pre_ping=True,
)

# Create session factory
# https://docs.sqlalchemy.org/en/20/orm/session_basics.html
SessionLocal = sessionmaker(
    expire_on_commit=False, autocommit=False, autoflush=False, bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    This provides a database session for each request and ensures
    it's properly closed after the request completes.

    Usage in FastAPI routes:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind: Engine = engine) -> None:
    """
    Initialize database tables.

    Creates all tables defined in Base metadata.
    Called during application startup; the test harness passes its own engine.
    """
    Base.metadata.create_all(bind=bind)
    _add_missing_columns(bind)
    _relabel_legacy_block_times(bind)


def _add_missing_columns(bind: Engine) -> None:
    """
    Add columns introduced after a table was first created.

    `create_all` never alters existing tables, so additive nullable columns
    are added here idempotently. Postgres only (tests use other dialects).
    """
    if bind.dialect.name != "postgresql":
        return
    with bind.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE datasets "
                "ADD COLUMN IF NOT EXISTS common_exam_groups JSONB DEFAULT NULL"
            )
        )


def _relabel_legacy_block_times(bind: Engine) -> None:
    """Move saved data to the corrected exam block times; one transaction."""
    if bind.dialect.name != "postgresql":
        return
    with bind.begin() as connection:
        relabel_block_times(connection)
