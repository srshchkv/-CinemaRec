from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import engine, Base
from app.api.routes import auth, movies, recommendations, ratings, admin
from app.recommendation.hybrid import get_recommender

from app.api.routes import posters

import app.models  # register all ORM models


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    get_recommender()  # pre-load ML models on startup
    yield


app = FastAPI(
    title="CinemaRec API",
    description="Hybrid Movie Recommendation System — Diploma Project",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(movies.router, prefix="/api/movies", tags=["Movies"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(ratings.router, prefix="/api/ratings", tags=["Ratings"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/", tags=["Health"])
def root():
    return {"service": "CinemaRec API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


app.include_router(posters.router, prefix="/api/posters", tags=["Posters"])