import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database.database import get_db
from app.models.movie import Movie

router = APIRouter()


class PosterResponse(BaseModel):
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    width: int = 500
    source: str = "omdb"
    skipped: bool = False


def _resolve_csv_path() -> Path | None:
    candidates = []
    if settings.CSV_PATH:
        candidates.append(Path(settings.CSV_PATH))
        candidates.append((Path(__file__).resolve().parents[4] / settings.CSV_PATH).resolve())
    candidates.extend([
        Path(__file__).resolve().parents[4] / "data_movies_ВКР2.csv",
        Path(__file__).resolve().parents[4] / "data_movies_ВКР.csv",
    ])
    for path in candidates:
        if path.exists():
            return path
    return None


@lru_cache(maxsize=1)
def _movie_imdb_map() -> dict[int, str]:
    csv_path = _resolve_csv_path()
    if not csv_path:
        return {}
    mapping: dict[int, str] = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            imdb_id = (row.get("imdb_id") or "").strip()
            if not imdb_id:
                continue
            try:
                movie_id = int(row["id"])
            except (TypeError, ValueError, KeyError):
                continue
            mapping[movie_id] = imdb_id
    return mapping


async def _resolve_omdb_poster(imdb_id: str) -> PosterResponse:
    if not imdb_id.startswith("tt"):
        return PosterResponse(skipped=True, source="invalid_imdb")
    if not settings.OMDB_API_KEY:
        return PosterResponse(skipped=True, source="omdb_key_missing")

    cache_key = imdb_id
    if cache_key in _POSTER_CACHE:
        return _POSTER_CACHE[cache_key]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {
                "apikey": settings.OMDB_API_KEY,
                "i": imdb_id,
                "plot": "short",
                "r": "json",
            }
            resp = await client.get("https://www.omdbapi.com/", params=params)
            resp.raise_for_status()
            payload = resp.json() or {}
    except Exception:
        result = PosterResponse(skipped=True, source="omdb_error")
        _POSTER_CACHE[cache_key] = result
        return result

    if payload.get("Response") == "False":
        result = PosterResponse(skipped=True, source="omdb_not_found")
        _POSTER_CACHE[cache_key] = result
        return result

    poster_url = payload.get("Poster")
    if not poster_url or poster_url == "N/A":
        result = PosterResponse(skipped=True, source="omdb_no_poster")
        _POSTER_CACHE[cache_key] = result
        return result

    result = PosterResponse(poster_url=poster_url, backdrop_url=None, skipped=False, source="omdb")
    if len(_POSTER_CACHE) > 5000:
        _POSTER_CACHE.clear()
    _POSTER_CACHE[cache_key] = result
    return result


_POSTER_CACHE: dict[str, PosterResponse] = {}


@router.get("/imdb/{imdb_id}", response_model=PosterResponse)
async def get_poster_by_imdb(imdb_id: str):
    return await _resolve_omdb_poster(imdb_id)


@router.get("/movie/{movie_id}", response_model=PosterResponse)
async def get_poster_by_movie_id(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if (
        movie
        and movie.poster_url
        and not movie.poster_url.startswith("https://image.tmdb.org")
        and not movie.poster_url.startswith("http://image.tmdb.org")
        and not movie.poster_url.startswith("//image.tmdb.org")
        and not movie.poster_url.startswith("/")
    ):
        return PosterResponse(
            poster_url=movie.poster_url,
            backdrop_url=None,
            skipped=False,
            source="db",
        )

    imdb_id = _movie_imdb_map().get(movie_id)
    if not imdb_id:
        return PosterResponse(skipped=True, source="csv_imdb_missing")

    result = await _resolve_omdb_poster(imdb_id)

    if movie and result.poster_url and movie.poster_url != result.poster_url:
        movie.poster_url = result.poster_url
        db.commit()

    return result
