import numpy as np
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.movie import Movie


def compute_popularity_score(vote_average: float, vote_count: int, popularity: float) -> float:
    """Weighted popularity: quality × log-votes × bounded-popularity."""
    quality = vote_average / 10.0
    log_votes = np.log1p(vote_count)
    bounded_pop = np.tanh(popularity / 500.0)
    return float(quality * log_votes * bounded_pop)


def get_popular_movies(db: Session, limit: int = 50, exclude_ids: List[int] = None) -> List[Movie]:
    # Pull a bounded candidate pool ordered by vote_count to avoid loading all 100k+ movies.
    # Python-sort the pool by the exact formula afterwards.
    pool_size = max(limit * 30, 2000)
    movies = (
        db.query(Movie)
        .filter(Movie.vote_count >= 100)
        .order_by(Movie.vote_count.desc())
        .limit(pool_size)
        .all()
    )

    if exclude_ids:
        exclude_set = set(exclude_ids)
        movies = [m for m in movies if m.id not in exclude_set]

    scored = sorted(
        movies,
        key=lambda m: compute_popularity_score(m.vote_average, m.vote_count, m.popularity),
        reverse=True,
    )
    return scored[:limit]


def score_movie(movie: Movie) -> float:
    return compute_popularity_score(movie.vote_average, movie.vote_count, movie.popularity)
