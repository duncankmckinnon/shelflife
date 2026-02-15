import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StartReadingRequest(BaseModel):
    started_at: dt.date | None = None  # defaults to today in the endpoint


class ReadingUpdate(BaseModel):
    started_at: dt.date | None = None
    finished_at: dt.date | None = None


class FinishReadingRequest(BaseModel):
    finished_at: dt.date | None = None  # defaults to today in the endpoint


class ReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    started_at: dt.date | None
    finished_at: dt.date | None
    duration_days: int | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    @model_validator(mode="after")
    def compute_duration(self):
        if self.started_at and self.finished_at:
            self.duration_days = (self.finished_at - self.started_at).days
        return self


class ReadingDetail(ReadingResponse):
    progress_entries: list["ReadingProgressResponse"] = []


class ReadingProgressCreate(BaseModel):
    page: int | None = Field(None, ge=0, description="Absolute page reached")
    pages_read: int | None = Field(None, ge=1, description="Pages read since last entry")
    start_page: int | None = Field(None, ge=0, description="Start page of range read")
    end_page: int | None = Field(None, ge=1, description="End page of range read")
    date: dt.date | None = None  # defaults to today in the endpoint

    @model_validator(mode="after")
    def validate_progress_input(self):
        has_page = self.page is not None
        has_pages_read = self.pages_read is not None
        has_range = self.start_page is not None or self.end_page is not None

        modes = sum([has_page, has_pages_read, has_range])
        if modes == 0:
            raise ValueError("Must provide one of: page, pages_read, or start_page+end_page")
        if modes > 1:
            raise ValueError("Provide only one of: page, pages_read, or start_page+end_page")

        if has_range:
            if self.start_page is None or self.end_page is None:
                raise ValueError("Both start_page and end_page are required for range input")
            if self.end_page <= self.start_page:
                raise ValueError("end_page must be greater than start_page")

        return self


class ReadingProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reading_id: int
    page: int
    date: dt.date
    created_at: dt.datetime
