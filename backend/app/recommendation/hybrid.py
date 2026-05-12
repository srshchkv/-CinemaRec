"""
Hybrid Recommender Engine.

Core ideas:
    - weighted hybrid of Collaborative + Content + Popularity + Click signals
    - rating-intent modeling (high ratings boost, low ratings penalize)
    - recency decay (new ratings/clicks have stronger influence)
    - candidate expansion via content neighbors (not only popular pool)

FinalScore (cold start, <5 ratings):
    0.60 × Content + 0.40 × Popularity
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.movie import Movie
from app.models.rating import Rating
from app.models.analytics import RecommendationClick
from app.recommendation.collaborative import CollaborativeModel
from app.recommendation.content_based import ContentBasedModel
from app.recommendation.popularity import score_movie, get_popular_movies
from app.recommendation.cold_start import is_cold_start, get_cold_start_recommendations

logger = logging.getLogger(__name__)

W_CF = 0.45
W_CB = 0.35
W_POP = 0.12
W_CLICK = 0.08

CANDIDATE_POOL = 100
CONTENT_EXPANSION_PER_SEED = 500
MAX_CONTENT_SEEDS = 80

RATING_HALF_LIFE_DAYS = 80
CLICK_HALF_LIFE_DAYS = 20

NEGATIVE_PENALTY_FACTOR = 0.60
NEGATIVE_BLOCK_THRESHOLD = 0.62
RECENT_DISLIKE_DAYS = 110


class HybridRecommender:
    def __init__(self):
        self.collaborative = CollaborativeModel(settings.MODELS_PATH)
        self.content = ContentBasedModel(settings.MODELS_PATH)
        self._initialized = False

    def initialize(self) -> None:
        cb_ok = self.content.load()
        cf_ok = self.collaborative.load()
        self._initialized = True
        logger.info(f"Recommender initialized — content={cb_ok}, collaborative={cf_ok}")

    @staticmethod
    def _decay_factor(ts: datetime | None, half_life_days: int) -> float:
        if ts is None:
            return 1.0
        now = datetime.utcnow()
        age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
        return 0.35 + 0.65 * (0.5 ** (age_days / max(1, half_life_days)))

    @staticmethod
    def _rating_intent_weight(rating: float) -> float:
        if rating >= 4.5:
            return 2.2
        if rating >= 4.0:
            return 1.4
        if rating >= 3.5:
            return 0.8
        if rating <= 2.0:
            return -2.2
        if rating <= 2.5:
            return -1.4
        return 0.0

    def get_recommendations(
        self,
        db: Session,
        user_id: int,
        n: int = 20,
    ) -> List[Movie]:
        user_ratings = (
            db.query(Rating)
            .filter(Rating.user_id == user_id)
            .order_by(Rating.timestamp.desc())
            .all()
        )
        rated_ids = {r.movie_id for r in user_ratings}

        positive_weighted: list[tuple[int, float]] = []
        negative_weighted: list[tuple[int, float]] = []
        recent_negative_present = False

        for r in user_ratings:
            intent = self._rating_intent_weight(float(r.rating))
            if intent == 0.0:
                continue
            decay = self._decay_factor(r.timestamp, RATING_HALF_LIFE_DAYS)
            weighted = intent * decay
            if weighted > 0:
                positive_weighted.append((r.movie_id, weighted))
            else:
                negative_weighted.append((r.movie_id, abs(weighted)))
                if r.timestamp and r.timestamp >= datetime.utcnow() - timedelta(days=RECENT_DISLIKE_DAYS):
                    recent_negative_present = True

        click_rows = (
            db.query(RecommendationClick.movie_id, RecommendationClick.timestamp)
            .filter(RecommendationClick.user_id == user_id)
            .order_by(RecommendationClick.timestamp.desc())
            .limit(200)
            .all()
        )
        click_weighted = [
            (movie_id, self._decay_factor(ts, CLICK_HALF_LIFE_DAYS))
            for movie_id, ts in click_rows
            if movie_id not in rated_ids
        ]

        if is_cold_start(len(user_ratings)):
            return get_cold_start_recommendations(
                db,
                self.content,
                positive_weighted,
                [mid for mid, _ in negative_weighted],
                n,
            )

        # Candidate generation: popular + content-neighbor expansion.
        candidates = get_popular_movies(db, limit=CANDIDATE_POOL, exclude_ids=list(rated_ids))
        candidate_ids = {m.id for m in candidates}
        candidate_map = {m.id: m for m in candidates}

        if self.content.is_loaded():
            top_pos_seeds = [mid for mid, _ in sorted(positive_weighted, key=lambda x: x[1], reverse=True)[:MAX_CONTENT_SEEDS]]
            top_click_seeds = [mid for mid, _ in click_weighted[:MAX_CONTENT_SEEDS // 2]]
            seed_ids = [*top_pos_seeds, *top_click_seeds]
            expanded_ids = self.content.expand_candidates(
                seed_ids,
                per_seed=CONTENT_EXPANSION_PER_SEED,
                exclude_ids=rated_ids,
            )
            candidate_ids.update(expanded_ids)

        missing_ids = [mid for mid in candidate_ids if mid not in candidate_map]
        if missing_ids:
            extra_movies = db.query(Movie).filter(Movie.id.in_(missing_ids)).all()
            for movie in extra_movies:
                candidate_map[movie.id] = movie
        candidate_ids = [mid for mid in candidate_ids if mid in candidate_map and mid not in rated_ids]

        # Content scores
        content_scores = {}
        if self.content.is_loaded() and positive_weighted:
            content_scores = self.content.score_for_user_weighted(positive_weighted, candidate_ids)

        click_scores = {}
        if self.content.is_loaded() and click_weighted:
            click_scores = self.content.score_for_user_weighted(click_weighted, candidate_ids)

        negative_scores = {}
        if self.content.is_loaded() and negative_weighted:
            negative_scores = self.content.score_for_user_weighted(negative_weighted, candidate_ids)

        # Collaborative scores
        cf_scores = {}
        if self.collaborative.is_loaded():
            cf_scores = self.collaborative.score_candidates(user_id, candidate_ids)

        # Popularity scores (normalize)
        pop_raw = {mid: score_movie(candidate_map[mid]) for mid in candidate_ids}
        max_pop = max(pop_raw.values()) if pop_raw else 1.0
        pop_scores = {mid: s / max_pop for mid, s in pop_raw.items()}

        # Combine
        final_scores = {}
        enabled_weight_sum = 0.0
        if cf_scores:
            enabled_weight_sum += W_CF
        if content_scores:
            enabled_weight_sum += W_CB
        if pop_scores:
            enabled_weight_sum += W_POP
        if click_scores:
            enabled_weight_sum += W_CLICK
        if enabled_weight_sum <= 1e-8:
            enabled_weight_sum = 1.0

        for mid in candidate_ids:
            cf = cf_scores.get(mid, 0.0)
            cb = content_scores.get(mid, 0.0)
            pop = pop_scores.get(mid, 0.0)
            click = click_scores.get(mid, 0.0)
            neg = max(0.0, negative_scores.get(mid, 0.0))

            if recent_negative_present and neg >= NEGATIVE_BLOCK_THRESHOLD:
                continue

            weighted_sum = W_CF * cf + W_CB * cb + W_POP * pop + W_CLICK * click
            normalized = weighted_sum / enabled_weight_sum
            penalty = NEGATIVE_PENALTY_FACTOR * neg
            final_scores[mid] = normalized - penalty

        top_ids = sorted(final_scores, key=final_scores.get, reverse=True)[:n]
        return [candidate_map[mid] for mid in top_ids]

    def get_similar(self, db: Session, movie_id: int, n: int = 10) -> List[Movie]:
        if self.content.is_loaded():
            similar_pairs = self.content.get_similar(movie_id, n)
            ids = [mid for mid, _ in similar_pairs]
            if ids:
                movies = db.query(Movie).filter(Movie.id.in_(ids)).all()
                movie_map = {m.id: m for m in movies}
                return [movie_map[mid] for mid in ids if mid in movie_map]

        return get_popular_movies(db, limit=n, exclude_ids=[movie_id])

    def get_popular(self, db: Session, n: int = 20) -> List[Movie]:
        return get_popular_movies(db, limit=n)


_recommender: Optional[HybridRecommender] = None


def get_recommender() -> HybridRecommender:
    global _recommender
    if _recommender is None:
        _recommender = HybridRecommender()
        _recommender.initialize()
    return _recommender
