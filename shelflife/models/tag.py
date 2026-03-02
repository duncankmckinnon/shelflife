import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class Tag(Base):
    __tablename__ = "tags"
    # Public tags: deduplicated by name via make_id (application-level).
    # Private tags: unique per (user_id, name) — enforced by DB.
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_id_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    sync_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    # NULL user_id = community/global tag; set = user-owned tag
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    books: Mapped[list["Book"]] = relationship(secondary="book_tags", back_populates="tags")
