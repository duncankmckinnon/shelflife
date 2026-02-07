from pydantic import BaseModel, ConfigDict


class TagCreate(BaseModel):
    name: str


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BulkTagCreate(BaseModel):
    tags: list[str]


class BulkTagResponse(BaseModel):
    tags: list[TagResponse]
    created: int
    skipped: int


class BulkBookTagCreate(BaseModel):
    tag: str
    book_ids: list[int]


class BulkBookTagResponse(BaseModel):
    tag: TagResponse
    tagged: int
    skipped: int
    not_found: list[int]
