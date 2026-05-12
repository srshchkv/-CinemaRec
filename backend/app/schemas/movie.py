from typing import Optional, List
from pydantic import BaseModel, field_validator


TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def normalize_poster_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"{TMDB_IMAGE_BASE}{value}"
    return value


class MovieBase(BaseModel):
    id: int
    title: str
    vote_average: float
    vote_count: int
    runtime: Optional[int] = None
    original_language: Optional[str] = None
    overview: Optional[str] = None
    popularity: float
    genres: Optional[str] = None
    keywords: Optional[str] = None
    year: Optional[int] = None
    poster_url: Optional[str] = None
    country: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("poster_url", mode="before")
    @classmethod
    def _normalize_poster_url(cls, value: Optional[str]) -> Optional[str]:
        return normalize_poster_url(value)


class MovieDetail(MovieBase):
    similar_movies: List[MovieBase] = []
    user_rating: Optional[float] = None
    clicks: int = 0
    views: int = 0


class MovieListItem(MovieBase):
    user_rating: Optional[float] = None


class MovieSearchResult(BaseModel):
    movies: List[MovieListItem]
    total: int
    page: int
    limit: int
    total_pages: int
