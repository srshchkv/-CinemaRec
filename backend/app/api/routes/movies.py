from typing import Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.movie import MovieSearchResult, MovieDetail
from app.services.movie_service import get_movies, get_movie_detail, track_click
from app.auth.dependencies import get_current_user_optional
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=MovieSearchResult)
def list_movies(
    q: Optional[str] = Query(None, description="Search query"),
    genre: Optional[str] = Query(None),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    language: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0.0, le=10.0),
    sort_by: str = Query("popularity", pattern="^(popularity|rating|year|votes)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    return get_movies(
        db, q=q, genre=genre, year_from=year_from, year_to=year_to,
        language=language, min_rating=min_rating, sort_by=sort_by,
        page=page, limit=limit,
        user_id=current_user.id if current_user else None,
    )


@router.get("/{movie_id}", response_model=MovieDetail)
def movie_detail(
    movie_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    track_click(db, movie_id)
    detail = get_movie_detail(db, movie_id, user_id=current_user.id if current_user else None)

    # Attach similar movies from recommendation engine
    from app.recommendation.hybrid import get_recommender
    recommender = get_recommender()
    similar = recommender.get_similar(db, movie_id, n=8)

    from app.schemas.movie import MovieBase
    detail.similar_movies = [MovieBase.model_validate(m) for m in similar]
    return detail
