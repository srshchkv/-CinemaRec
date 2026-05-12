import os
import pickle
from typing import List, Tuple, Optional


class CollaborativeModel:
    """Wrapper around a pre-trained Surprise SVD model."""

    def __init__(self, models_path: str):
        self._models_path = models_path
        self._algo = None
        self._loaded = False

    def load(self) -> bool:
        path = os.path.join(self._models_path, "svd_model.pkl")
        if not os.path.exists(path):
            return False
        with open(path, "rb") as f:
            self._algo = pickle.load(f)
        self._loaded = True
        return True

    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, user_id: int, movie_id: int) -> float:
        """Predict rating for user-movie pair. Returns 0 if model not loaded."""
        if not self._loaded:
            return 0.0
        try:
            pred = self._algo.predict(str(user_id), str(movie_id))
            return float(pred.est)
        except Exception:
            return 0.0

    def score_candidates(self, user_id: int, candidate_ids: List[int]) -> dict[int, float]:
        """Score multiple candidates. Returns normalized 0-1 scores."""
        if not self._loaded:
            return {}
        raw = {mid: self.predict(user_id, mid) for mid in candidate_ids}
        if not raw:
            return {}
        min_score = min(raw.values())
        max_score = max(raw.values())
        if max_score == min_score:
            return {mid: 0.5 for mid in raw}
        return {mid: (s - min_score) / (max_score - min_score) for mid, s in raw.items()}
