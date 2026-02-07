from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class ShelfBook(Base):
    __tablename__ = "shelf_books"
    __table_args__ = (UniqueConstraint("shelf_id", "book_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shelf_id: Mapped[int] = mapped_column(ForeignKey("shelves.id", ondelete="CASCADE"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    date_added: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    date_read: Mapped[date | None] = mapped_column(Date)

    shelf: Mapped["Shelf"] = relationship(back_populates="book_links")
    book: Mapped["Book"] = relationship(back_populates="shelf_links")


class Shelf(Base):
    __tablename__ = "shelves"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    book_links: Mapped[list["ShelfBook"]] = relationship(back_populates="shelf", cascade="all, delete-orphan")
