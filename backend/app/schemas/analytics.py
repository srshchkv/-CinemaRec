from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class AdminStats(BaseModel):
    total_users: int
    total_movies: int
    total_ratings: int
    avg_rating: float
    registrations_last_7d: int


class MovieAnalyticsItem(BaseModel):
    movie_id: int
    title: str
    clicks: int
    views: int
    ctr: float


class GenreStat(BaseModel):
    genre: str
    count: int


class YearStat(BaseModel):
    year: int
    count: int


class AnalyticsDashboard(BaseModel):
    top_clicked: List[MovieAnalyticsItem]
    genre_distribution: List[GenreStat]
    year_distribution: List[YearStat]
    language_distribution: List[Dict[str, Any]]


class ModelMetrics(BaseModel):
    precision_at_10: float
    recall_at_10: float
    ndcg_at_10: float
    rmse: Optional[float] = None
    coverage: Optional[float] = None
