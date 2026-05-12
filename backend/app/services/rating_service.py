from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.rating import Rating
from app.models.movie import Movie
from app.schemas.rating import RatingCreate, RatingResponse


def _to_rating_response(rating: Rating, movie_title: str | None = None) -> RatingResponse:
    response = RatingResponse.model_validate(rating)
    if movie_title is not None:
        response = response.model_copy(update={"movie_title": movie_title})
    return response


def upsert_rating(db: Session, user_id: int, data: RatingCreate) -> RatingResponse:
    movie = db.query(Movie).filter(Movie.id == data.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    existing = db.query(Rating).filter(
        Rating.user_id == user_id, Rating.movie_id == data.movie_id
    ).first()

    if existing:
        existing.rating = data.rating
        existing.timestamp = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return _to_rating_response(existing, movie.title)

    rating = Rating(user_id=user_id, movie_id=data.movie_id, rating=data.rating)
    db.add(rating)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(Rating).filter(
            Rating.user_id == user_id,
            Rating.movie_id == data.movie_id,
        ).first()
        if not existing:
            raise HTTPException(status_code=409, detail="Failed to save rating")
        existing.rating = data.rating
        existing.timestamp = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return _to_rating_response(existing, movie.title)

    db.refresh(rating)
    return _to_rating_response(rating, movie.title)


def get_user_ratings(db: Session, user_id: int) -> list[RatingResponse]:
    rows = (
        db.query(Rating, Movie.title)
        .join(Movie, Movie.id == Rating.movie_id)
        .filter(Rating.user_id == user_id)
        .order_by(Rating.timestamp.desc())
        .all()
    )
    return [_to_rating_response(r, title) for r, title in rows]


def delete_rating(db: Session, user_id: int, movie_id: int) -> None:
    rating = db.query(Rating).filter(
        Rating.user_id == user_id,
        Rating.movie_id == movie_id,
    ).first()
    if not rating:
        raise HTTPException(status_code=404, detail="Оценка для фильма не найдена")

    db.delete(rating)
    db.commit()


def count_user_ratings(db: Session, user_id: int) -> int:
    return db.query(Rating).filter(Rating.user_id == user_id).count()
