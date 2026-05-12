"""
Offline hybrid recommender (used by evaluation pipeline, not the backend).
Backend uses backend/app/recommendation/hybrid.py with live DB queries.
This module provides a self-contained scorer for batch evaluation.
"""
import pickle
import numpy as np
from pathlib import Path
from scipy.sparse import load_npz
from sklearn.metrics.pairwise import cosine_similarity


MODELS_DIR = Path(__file__).parent.parent / "models"

W_CF = 0.55
W_CB = 0.25
W_POP = 0.12
W_CLICK = 0.08


class OfflineHybridScorer:
    def __init__(self):
        self.algo = None
        self.tfidf_matrix = None
        self.movie_ids: list[int] = []
        self.id_to_idx: dict[int, int] = {}

    def load(self) -> bool:
        ok = True
        svd_path = MODELS_DIR / "svd_model.pkl"
        tfidf_path = MODELS_DIR / "tfidf_matrix.npz"
        ids_path = MODELS_DIR / "movie_ids.pkl"

        if svd_path.exists():
            with open(svd_path, "rb") as f:
                self.algo = pickle.load(f)
        else:
            print("[hybrid] SVD model not found — CF disabled")
            ok = False

        if tfidf_path.exists() and ids_path.exists():
            self.tfidf_matrix = load_npz(tfidf_path).toarray()
            with open(ids_path, "rb") as f:
                self.movie_ids = pickle.load(f)
            self.id_to_idx = {mid: i for i, mid in enumerate(self.movie_ids)}
        else:
            print("[hybrid] TF-IDF model not found — CB disabled")
            ok = False

        return ok

    def score(
        self,
        user_id: int,
        candidate_ids: list[int],
        liked_ids: list[int],
        pop_scores: dict[int, float],
    ) -> dict[int, float]:
        cf_scores = {}
        if self.algo:
            for mid in candidate_ids:
                try:
                    cf_scores[mid] = self.algo.predict(str(user_id), str(mid)).est / 5.0
                except Exception:
                    cf_scores[mid] = 0.0

        cb_scores = {}
        if self.tfidf_matrix is not None and liked_ids:
            liked_idx = [self.id_to_idx[m] for m in liked_ids if m in self.id_to_idx]
            if liked_idx:
                profile = self.tfidf_matrix[liked_idx].mean(axis=0).reshape(1, -1)
                for mid in candidate_ids:
                    if mid in self.id_to_idx:
                        vec = self.tfidf_matrix[self.id_to_idx[mid]].reshape(1, -1)
                        cb_scores[mid] = float(cosine_similarity(profile, vec)[0][0])

        max_pop = max(pop_scores.values()) if pop_scores else 1.0

        result = {}
        for mid in candidate_ids:
            cf = cf_scores.get(mid, 0.0)
            cb = cb_scores.get(mid, 0.0)
            pop = pop_scores.get(mid, 0.0) / max_pop if max_pop > 0 else 0.0
            result[mid] = W_CF * cf + W_CB * cb + W_POP * pop
        return result
