import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_api_key_hash", "api_key_hash", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    library: Mapped[list["UserBook"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    shelves: Mapped[list["Shelf"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    readings: Mapped[list["Reading"]] = relationship(back_populates="user", cascade="all, delete-orphan")
