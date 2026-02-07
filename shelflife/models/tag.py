from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shelflife.database import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    books: Mapped[list["Book"]] = relationship(secondary="book_tags", back_populates="tags")
