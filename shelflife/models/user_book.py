import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class UserBook(Base):
    __tablename__ = "user_books"
    __table_args__ = (UniqueConstraint("user_id", "book_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    sync_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="library")
    book: Mapped["Book"] = relationship(back_populates="user_books")


async def ensure_user_book(session: AsyncSession, user_id: int, book_id: int) -> UserBook:
    from shelflife.id import make_id

    stmt = select(UserBook).where(UserBook.user_id == user_id, UserBook.book_id == book_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing
    ub = UserBook(id=make_id(user_id, book_id), user_id=user_id, book_id=book_id)
    session.add(ub)
    return ub
