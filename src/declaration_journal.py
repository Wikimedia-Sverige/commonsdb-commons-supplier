import inspect
import logging
from datetime import datetime
from typing import Optional

import alembic
from alembic.config import Config
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Declaration(Base):
    __tablename__ = "declaration"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_timestamp: Mapped[datetime]
    updated_timestamp: Mapped[datetime]
    page_id: Mapped[int]
    revision_id: Mapped[int]
    image_hash: Mapped[Optional[str]] = mapped_column(String(41))
    file_size: Mapped[Optional[int]]
    download_time: Mapped[Optional[float]]
    iscc: Mapped[Optional[str]] = mapped_column(String(61))
    iscc_time: Mapped[Optional[float]]

    def __repr__(self) -> str:
        fields = {}
        for attribute, value in inspect.getmembers(self):
            if attribute in ["registry", "metadata"]:
                # These come from DeclarativeBase.
                continue

            if attribute.startswith("_"):
                continue

            fields[attribute] = value

        return f"Declaration {fields}"


class DeclarationJournal:
    def __init__(self, engine, session):
        self._session = session
        if engine.url != "sqlite:///:memory:":
            # The is mostly for testing.
            Base.metadata.create_all(engine)
        else:
            # Make sure that the database is up to date.
            alembic_cfg = Config("alembic.ini")
            alembic.command.upgrade(alembic_cfg, "head")

    def add_declaration(self, **kwargs) -> Declaration:
        now = datetime.now()
        declaration = Declaration(
            created_timestamp=now,
            updated_timestamp=now,
            **kwargs
        )
        self._session.add(declaration)
        self._session.commit()
        return declaration

    def update_declaration(self, declaration: Declaration, **kwargs):
        if declaration is None:
            return

        for field, value in kwargs.items():
            if not hasattr(declaration, field):
                logger.warning(f"Not updating unknown field: '{field}'.")
                continue

            setattr(declaration, field, value)

        declaration.updated_timestamp = datetime.now()
        self._session.commit()

    def get_declarations(self) -> list[Declaration]:
        statement = select(Declaration)
        result = self._session.scalars(statement).all()

        return result

    def get_page_id_match(self, page_id: int) -> Declaration:
        statement = select(Declaration).where(Declaration.page_id == page_id)
        declaration = self._session.scalars(statement).one_or_none()
        if declaration is None:
            return None

        return declaration

    def get_image_hash_match(self, hash: str) -> Declaration:
        statement = select(Declaration).where(Declaration.image_hash == hash)
        declaration = self._session.scalars(statement).one_or_none()
        if declaration is None:
            return None

        return declaration


def create_journal(database_url: str):
    engine = create_engine(database_url)
    with Session(engine, expire_on_commit=False) as session, session.begin():
        journal = DeclarationJournal(engine, session)

    return journal
