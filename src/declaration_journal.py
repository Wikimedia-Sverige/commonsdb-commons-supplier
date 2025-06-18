from datetime import datetime

import alembic
from alembic.config import Config
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Declaration(Base):
    __tablename__ = "declaration"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_timestamp: Mapped[datetime]
    updated_timestamp: Mapped[datetime]
    page_id: Mapped[int]
    revision_id: Mapped[int]
    image_hash: Mapped[str] = mapped_column(String(41), nullable=True)
    iscc: Mapped[str] = mapped_column(String(61), nullable=True)

    def __repr__(self) -> str:
        return f"Declaration(id={self.id!r}, created_timestamp={self.created_timestamp!r}, updated_timestamp={self.updated_timestamp!r}, page_id={self.page_id!r}, revision_id={self.revision_id!r}, image_hash={self.image_hash!r}, iscc={self.iscc!r})"  # noqa: E501


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

    def add_declaration(
        self,
        page_id: int,
        revision_id: int,
        image_hash: str
    ) -> Declaration:
        declaration = Declaration(
            page_id=page_id,
            created_timestamp=datetime.now(),
            updated_timestamp=datetime.now(),
            revision_id=revision_id,
            image_hash=image_hash
        )
        self._session.add(declaration)
        self._session.commit()
        return declaration

    def update_declaration(
        self,
        declaration: Declaration,
        revision_id: int | None = None,
        image_hash: str | None = None,
        iscc: str | None = None
    ):
        if declaration is None:
            return

        changed = False
        if revision_id is not None:
            declaration.revision_id = revision_id
            changed = True
        if image_hash is not None:
            declaration.image_hash = image_hash
            changed = True
        if iscc is not None:
            declaration.iscc = iscc
            changed = True

        if changed:
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
