from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    started_at: Mapped[date | None] = mapped_column(Date)
    finished_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    book: Mapped["Book"] = relationship(back_populates="readings")
    progress_entries: Mapped[list["ReadingProgress"]] = relationship(
        back_populates="reading", cascade="all, delete-orphan", order_by="ReadingProgress.date"
    )


class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    __table_args__ = (UniqueConstraint("reading_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    reading_id: Mapped[int] = mapped_column(ForeignKey("readings.id", ondelete="CASCADE"))
    page: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    reading: Mapped["Reading"] = relationship(back_populates="progress_entries")
