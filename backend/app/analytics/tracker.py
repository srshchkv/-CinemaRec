from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from app.models.analytics import MovieClick, RecommendationClick
from app.models.movie import Movie
from app.models.user import User
from app.models.rating import Rating
from app.schemas.analytics import AdminStats, AnalyticsDashboard, MovieAnalyticsItem, GenreStat, YearStat


def track_movie_view(db: Session, movie_id: int) -> None:
    stat = db.query(MovieClick).filter(MovieClick.movie_id == movie_id).first()
    if stat is None:
        stat = MovieClick(movie_id=movie_id, views=1, clicks=0)
        db.add(stat)
    else:
        stat.views += 1
    db.commit()


def track_recommendation_click(db: Session, user_id: int, movie_id: int, source: str = "recommendation") -> None:
    click = RecommendationClick(user_id=user_id, movie_id=movie_id, source=source)
    db.add(click)

    stat = db.query(MovieClick).filter(MovieClick.movie_id == movie_id).first()
    if stat is None:
        stat = MovieClick(movie_id=movie_id, clicks=1, views=0)
        db.add(stat)
    else:
        stat.clicks += 1
    db.commit()


def get_admin_stats(db: Session) -> AdminStats:
    week_ago = datetime.utcnow() - timedelta(days=7)
    return AdminStats(
        total_users=db.query(User).count(),
        total_movies=db.query(Movie).count(),
        total_ratings=db.query(Rating).count(),
        avg_rating=float(db.query(func.avg(Rating.rating)).scalar() or 0.0),
        registrations_last_7d=db.query(User).filter(User.created_at >= week_ago).count(),
    )


def get_analytics_dashboard(db: Session) -> AnalyticsDashboard:
    # Top clicked movies
    top_clicks = (
        db.query(MovieClick, Movie)
        .join(Movie, MovieClick.movie_id == Movie.id)
        .order_by(desc(MovieClick.clicks))
        .limit(10)
        .all()
    )
    top_clicked = [
        MovieAnalyticsItem(
            movie_id=mc.movie_id,
            title=m.title,
            clicks=mc.clicks,
            views=mc.views,
            ctr=mc.ctr,
        )
        for mc, m in top_clicks
    ]

    # Genre distribution (count movies per genre)
    movies_with_genres = db.query(Movie.genres).filter(Movie.genres.isnot(None)).all()
    genre_counter: dict[str, int] = {}
    for (genres_str,) in movies_with_genres:
        for g in genres_str.split(","):
            g = g.strip()
            if g:
                genre_counter[g] = genre_counter.get(g, 0) + 1
    genre_dist = [
        GenreStat(genre=g, count=c)
        for g, c in sorted(genre_counter.items(), key=lambda x: x[1], reverse=True)[:15]
    ]

    # Year distribution
    year_rows = (
        db.query(Movie.year, func.count(Movie.id))
        .filter(Movie.year.isnot(None))
        .group_by(Movie.year)
        .order_by(Movie.year)
        .all()
    )
    year_dist = [YearStat(year=y, count=c) for y, c in year_rows if y]

    # Language distribution
    lang_rows = (
        db.query(Movie.original_language, func.count(Movie.id))
        .filter(Movie.original_language.isnot(None))
        .group_by(Movie.original_language)
        .order_by(desc(func.count(Movie.id)))
        .limit(10)
        .all()
    )
    lang_dist = [{"language": lang, "count": cnt} for lang, cnt in lang_rows]

    return AnalyticsDashboard(
        top_clicked=top_clicked,
        genre_distribution=genre_dist,
        year_distribution=year_dist,
        language_distribution=lang_dist,
    )
