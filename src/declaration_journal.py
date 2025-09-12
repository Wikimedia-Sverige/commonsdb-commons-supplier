import inspect
import logging
from datetime import datetime
from typing import List, Optional, Set

import alembic
from alembic.config import Config
from sqlalchemy import Column, ForeignKey, String, Table, create_engine, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship
)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


tag_association = Table(
    "tag_association",
    Base.metadata,
    Column("declartion_id", ForeignKey("declaration.id"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id"), primary_key=True),
)


class Declaration(Base):
    __tablename__ = "declaration"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_timestamp: Mapped[datetime]
    updated_timestamp: Mapped[datetime]
    page_id: Mapped[int]
    revision_id: Mapped[int]
    image_hash: Mapped[Optional[str]] = mapped_column(String(41))
    file_size: Mapped[Optional[int]]
    width: Mapped[Optional[int]]
    height: Mapped[Optional[int]]
    download_time: Mapped[Optional[float]]
    iscc: Mapped[Optional[str]] = mapped_column(String(61))
    iscc_time: Mapped[Optional[float]]
    tags: Mapped[Set["Tag"]] = relationship(secondary=tag_association)
    ingested_cid: Mapped[Optional[str]] = mapped_column(String(57))

    def __repr__(self) -> str:
        fields = get_fields(self)
        return f"Declaration {fields}"


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(50))

    def __repr__(self) -> str:
        fields = get_fields(self)
        return f"Tag {fields}"

    def __eq__(self, other):
        return other.label == other.label

    def __hash__(self):
        return hash(self.label)


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

    def add_declaration(self, tag_labels: List[str], **kwargs) -> Declaration:
        tags = set()
        for label in tag_labels:
            statement = select(Tag).where(Tag.label == label)
            tag = self._session.scalars(statement).one_or_none()
            if tag is None:
                tag = Tag(label=label)
                self._session.add(tag)
            tags.add(tag)

        now = datetime.now()
        declaration = Declaration(
            created_timestamp=now,
            updated_timestamp=now,
            tags=tags,
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

    def get_declarations(self, tag: str = None) -> list[Declaration]:
        statement = select(Declaration)
        if tag is not None:
            statement = statement.join(Declaration.tags.and_(Tag.label == tag))

        declarations = self._session.scalars(statement).all()
        return declarations

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

    def tag_exists(self, name: str) -> bool:
        statement = select(Tag).where(Tag.label == name)
        tag = self._session.scalars(statement).one_or_none()

        return tag is not None


def create_journal(database_url: str) -> DeclarationJournal:
    engine = create_engine(database_url)
    with Session(engine, expire_on_commit=False) as session, session.begin():
        journal = DeclarationJournal(engine, session)

    return journal


def get_fields(journal_item) -> dict:
    fields = {}
    for attribute, value in inspect.getmembers(journal_item):
        if attribute in ["registry", "metadata"]:
            # These come from DeclarativeBase.
            continue

        if attribute.startswith("_"):
            continue

        fields[attribute] = value

    return fields
