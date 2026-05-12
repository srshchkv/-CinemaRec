from datetime import datetime
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from app.database.database import Base


class MovieClick(Base):
    __tablename__ = "movie_clicks"

    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), unique=True, nullable=False)
    clicks = Column(Integer, default=0)
    views = Column(Integer, default=0)

    movie = relationship("Movie", back_populates="click_stat")

    @property
    def ctr(self) -> float:
        if self.views == 0:
            return 0.0
        return round(self.clicks / self.views, 4)


class RecommendationClick(Base):
    __tablename__ = "recommendation_clicks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    source = Column(String(32), default="recommendation")
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="rec_clicks")
    movie = relationship("Movie", back_populates="rec_clicks")
