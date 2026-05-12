from datetime import datetime
from pydantic import BaseModel, Field


class RatingCreate(BaseModel):
    movie_id: int
    rating: float = Field(..., ge=0.5, le=5.0)


class RatingResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    movie_title: str | None = None
    rating: float
    timestamp: datetime

    model_config = {"from_attributes": True}
