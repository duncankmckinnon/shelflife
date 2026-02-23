from pydantic import BaseModel


class BookRef(BaseModel):
    """Identifies a book by title and author."""

    title: str
    author: str