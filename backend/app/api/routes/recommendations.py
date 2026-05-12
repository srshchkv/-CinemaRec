from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database.database import get_db
from app.schemas.movie import MovieBase
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.recommendation.hybrid import get_recommender
from app.analytics.tracker import track_recommendation_click

router = APIRouter()

class RecommendationClickPayload(BaseModel):
    movie_id: int
    source: str = "recommendation"


@router.get("/", response_model=list[MovieBase])
def personal_recommendations(
    n: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recommender = get_recommender()
    movies = recommender.get_recommendations(db, current_user.id, n=n)
    return [MovieBase.model_validate(m) for m in movies]


@router.get("/popular", response_model=list[MovieBase])
def popular_movies(
    n: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    recommender = get_recommender()
    movies = recommender.get_popular(db, n=n)
    return [MovieBase.model_validate(m) for m in movies]


@router.get("/similar/{movie_id}", response_model=list[MovieBase])
def similar_movies(
    movie_id: int,
    n: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    recommender = get_recommender()
    movies = recommender.get_similar(db, movie_id, n=n)
    return [MovieBase.model_validate(m) for m in movies]


@router.post("/click", status_code=204)
def recommendation_click(
    data: RecommendationClickPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    track_recommendation_click(db, current_user.id, data.movie_id, data.source)
