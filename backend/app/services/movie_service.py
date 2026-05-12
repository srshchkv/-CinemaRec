import math
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from app.models.movie import Movie
from app.models.rating import Rating
from app.models.analytics import MovieClick
from app.schemas.movie import MovieSearchResult, MovieListItem, MovieDetail


def get_movies(
    db: Session,
    q: Optional[str] = None,
    genre: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    language: Optional[str] = None,
    min_rating: Optional[float] = None,
    sort_by: str = "popularity",
    page: int = 1,
    limit: int = 20,
    user_id: Optional[int] = None,
) -> MovieSearchResult:
    query = db.query(Movie)

    if q:
        query = query.filter(
            or_(
                Movie.title.ilike(f"%{q}%"),
                Movie.overview.ilike(f"%{q}%"),
            )
        )
    if genre:
        query = query.filter(Movie.genres.ilike(f"%{genre}%"))
    if year_from:
        query = query.filter(Movie.year >= year_from)
    if year_to:
        query = query.filter(Movie.year <= year_to)
    if language:
        query = query.filter(Movie.original_language == language)
    if min_rating is not None:
        query = query.filter(Movie.vote_average >= min_rating)

    sort_map = {
        "popularity": Movie.popularity.desc(),
        "rating": Movie.vote_average.desc(),
        "year": Movie.year.desc(),
        "votes": Movie.vote_count.desc(),
    }
    query = query.order_by(sort_map.get(sort_by, Movie.popularity.desc()))

    total = query.count()
    movies = query.offset((page - 1) * limit).limit(limit).all()

    user_ratings: dict[int, float] = {}
    if user_id:
        ratings = db.query(Rating).filter(
            Rating.user_id == user_id,
            Rating.movie_id.in_([m.id for m in movies]),
        ).all()
        user_ratings = {r.movie_id: r.rating for r in ratings}

    items = []
    for m in movies:
        item = MovieListItem.model_validate(m)
        item.user_rating = user_ratings.get(m.id)
        items.append(item)

    return MovieSearchResult(
        movies=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=math.ceil(total / limit),
    )


def get_movie_detail(db: Session, movie_id: int, user_id: Optional[int] = None) -> MovieDetail:
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    user_rating = None
    if user_id:
        r = db.query(Rating).filter(Rating.user_id == user_id, Rating.movie_id == movie_id).first()
        if r:
            user_rating = r.rating

    clicks = views = 0
    if movie.click_stat:
        clicks = movie.click_stat.clicks
        views = movie.click_stat.views

    detail = MovieDetail.model_validate(movie)
    detail.user_rating = user_rating
    detail.clicks = clicks
    detail.views = views
    return detail


def search_movies(db: Session, q: str, limit: int = 10) -> list[Movie]:
    return (
        db.query(Movie)
        .filter(Movie.title.ilike(f"%{q}%"))
        .order_by(Movie.popularity.desc())
        .limit(limit)
        .all()
    )


def track_click(db: Session, movie_id: int) -> None:
    stat = db.query(MovieClick).filter(MovieClick.movie_id == movie_id).first()
    if stat is None:
        stat = MovieClick(movie_id=movie_id, clicks=1, views=1)
        db.add(stat)
    else:
        stat.clicks += 1
        stat.views += 1
    db.commit()
