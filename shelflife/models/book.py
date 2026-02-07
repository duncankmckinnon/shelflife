from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class BookTag(Base):
    __tablename__ = "book_tags"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(String(300), nullable=False)
    additional_authors: Mapped[str | None] = mapped_column(String(500))
    isbn: Mapped[str | None] = mapped_column(String(13), unique=True)
    isbn13: Mapped[str | None] = mapped_column(String(17), unique=True)
    publisher: Mapped[str | None] = mapped_column(String(300))
    page_count: Mapped[int | None] = mapped_column(Integer)
    year_published: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    goodreads_id: Mapped[str | None] = mapped_column(String(20), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    reviews: Mapped[list["Review"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    shelf_links: Mapped[list["ShelfBook"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(secondary="book_tags", back_populates="books")
