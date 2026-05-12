from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.rating import RatingCreate, RatingResponse
from app.services.rating_service import upsert_rating, get_user_ratings, delete_rating
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=RatingResponse, status_code=201)
def rate_movie(
    data: RatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return upsert_rating(db, current_user.id, data)


@router.get("/my", response_model=list[RatingResponse])
def my_ratings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_ratings(db, current_user.id)


@router.delete("/{movie_id}", status_code=204, response_class=Response)
def remove_rating(
    movie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_rating(db, current_user.id, movie_id)
    return Response(status_code=204)
