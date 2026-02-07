from pydantic import BaseModel, ConfigDict


class TagCreate(BaseModel):
    name: str


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
