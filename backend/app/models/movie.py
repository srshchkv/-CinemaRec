from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.orm import relationship
from app.database.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False, index=True)
    vote_average = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)
    runtime = Column(Integer, nullable=True)
    original_language = Column(String(10), nullable=True)
    overview = Column(Text, nullable=True)
    popularity = Column(Float, default=0.0)
    genres = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    year = Column(Integer, nullable=True, index=True)
    poster_url = Column(String(512), nullable=True)
    country = Column(String(128), nullable=True)

    ratings = relationship("Rating", back_populates="movie", cascade="all, delete-orphan")
    click_stat = relationship("MovieClick", back_populates="movie", uselist=False, cascade="all, delete-orphan")
    rec_clicks = relationship("RecommendationClick", back_populates="movie", cascade="all, delete-orphan")
