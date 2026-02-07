from pydantic import BaseModel


class HashResponse(BaseModel):
    id: int
    parts: list[str]
