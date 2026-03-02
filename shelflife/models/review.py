import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("book_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    sync_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[float | None] = mapped_column(Float)
    review_text: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    book: Mapped["Book"] = relationship(back_populates="reviews")
    user: Mapped["User"] = relationship(back_populates="reviews")
