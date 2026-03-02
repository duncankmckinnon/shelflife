import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class ShelfBook(Base):
    __tablename__ = "shelf_books"
    __table_args__ = (UniqueConstraint("shelf_id", "book_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    sync_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    shelf_id: Mapped[int] = mapped_column(ForeignKey("shelves.id", ondelete="CASCADE"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    date_read: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    shelf: Mapped["Shelf"] = relationship(back_populates="book_links")
    book: Mapped["Book"] = relationship(back_populates="shelf_links")


class Shelf(Base):
    __tablename__ = "shelves"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    sync_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    book_links: Mapped[list["ShelfBook"]] = relationship(back_populates="shelf", cascade="all, delete-orphan")
    user: Mapped["User"] = relationship(back_populates="shelves")
