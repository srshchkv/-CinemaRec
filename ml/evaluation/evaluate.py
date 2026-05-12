"""
Оффлайн-оценка гибридной рекомендательной системы.
Схема leave-one-out: скрываем последнюю оценку пользователя и измеряем качество.
"""
import sys
import json
import random
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import load_npz

from ml.evaluation.metrics import average_metrics, rmse
from ml.svd.collaborative_model import load_ratings_from_db

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
K = 20
SAMPLE_USERS = 100
MIN_RATINGS_PER_USER = 100


def _intent_weight(rating: float) -> float:
    if rating >= 4.5:
        return 2.2
    if rating >= 4.0:
        return 1.4
    if rating >= 3.5:
        return 0.9
    if rating <= 2.0:
        return -2.2
    if rating <= 2.5:
        return -1.3
    return 0.0


def _load_ratings() -> pd.DataFrame:
    """Загружает оценки из configured DB или возвращает пустой DataFrame."""
    return load_ratings_from_db()


def _load_models():
    """Загружает TF-IDF и SVD модели. Возвращает (matrix, movie_ids, id_to_idx, algo)."""
    matrix, movie_ids, id_to_idx, algo = None, [], {}, None

    tfidf_path = MODELS_DIR / "tfidf_matrix.npz"
    ids_path = MODELS_DIR / "movie_ids.pkl"
    svd_path = MODELS_DIR / "svd_model.pkl"

    if tfidf_path.exists() and ids_path.exists():
        matrix = load_npz(tfidf_path).toarray()
        with open(ids_path, "rb") as f:
            movie_ids = pickle.load(f)
        id_to_idx = {mid: i for i, mid in enumerate(movie_ids)}

    if svd_path.exists():
        with open(svd_path, "rb") as f:
            algo = pickle.load(f)

    return matrix, movie_ids, id_to_idx, algo


def evaluate():
    ratings = _load_ratings()
    matrix, movie_ids, id_to_idx, algo = _load_models()

    if matrix is None and algo is None:
        print("[eval] Модели не найдены в ml/models/ — оценка пропущена.")
        print("       Сначала запустите обучение через ml/main.py.")
        return

    if len(ratings) < MIN_RATINGS_PER_USER * 5:
        # Если в БД мало оценок, используем синтетические данные.
        print("[eval] Недостаточно оценок в БД, запускаю оценку на синтетических данных…")
        from ml.svd.collaborative_model import generate_synthetic_ratings
        # Берем небольшой поднабор фильмов для быстрой оценки.
        try:
            from ml.preprocessing.load_data import load_movies
            df = load_movies()
            ratings = generate_synthetic_ratings(df, n_users=100, ratings_per_user=500)
        except Exception as e:
            print(f"[eval] Не удалось сгенерировать синтетические оценки: {e}")
            _save_dummy_metrics()
            return

    if movie_ids:
        ratings = ratings[ratings["movie_id"].isin(set(movie_ids))]

    # Global popularity proxy from observed interactions.
    item_counts = ratings["movie_id"].value_counts()
    max_count = int(item_counts.max()) if len(item_counts) else 1

    # Оставляем только пользователей с достаточным числом оценок.
    user_counts = ratings.groupby("user_id").size()
    eligible = user_counts[user_counts >= MIN_RATINGS_PER_USER].index.tolist()
    if not eligible:
        print("[eval] Недостаточно пользователей с нужным количеством оценок.")
        _save_dummy_metrics()
        return

    if len(eligible) > SAMPLE_USERS:
        eligible = random.sample(eligible, SAMPLE_USERS)

    print(f"[eval] Оценка на {len(eligible)} пользователях…")

    all_movie_ids = set(movie_ids) if movie_ids else set()
    users_data = []
    rmse_pairs = []

    for user_id in eligible:
        sort_col = "timestamp" if "timestamp" in ratings.columns else "movie_id"
        user_ratings = ratings[ratings["user_id"] == user_id].sort_values(sort_col)
        positive = user_ratings[user_ratings["rating"] >= 4.0]
        if len(user_ratings) < MIN_RATINGS_PER_USER or len(positive) < 4:
            continue

        # Leave-multi-liked-out: скрываем несколько релевантных фильмов,
        # чтобы Precision@K / Recall@K были более информативными.
        holdout_size = min(3, max(1, len(positive) // 5))
        holdout_rows = positive.sample(n=holdout_size, random_state=42)
        holdout_ids = set(int(mid) for mid in holdout_rows["movie_id"].tolist())
        train_rows = user_ratings[~user_ratings["movie_id"].isin(holdout_ids)]
        relevant = holdout_ids

        weighted_positive = []
        weighted_negative = []
        train_ordered = train_rows.reset_index(drop=True)
        total_rows = max(1, len(train_ordered))
        for idx, row in train_ordered.iterrows():
            intent = _intent_weight(float(row["rating"]))
            if intent == 0:
                continue
            recency = 0.4 + 0.6 * ((idx + 1) / total_rows)
            weighted = intent * recency
            movie_id = int(row["movie_id"])
            if weighted > 0:
                weighted_positive.append((movie_id, weighted))
            else:
                weighted_negative.append((movie_id, abs(weighted)))

        trained_ids = set(train_rows["movie_id"].tolist())
        candidates_pool = list(all_movie_ids - trained_ids)
        candidates_pool = [mid for mid in candidates_pool if mid not in relevant]
        sample_n = min(500 - len(relevant), len(candidates_pool))
        sampled = random.sample(candidates_pool, sample_n) if sample_n else []
        candidates = [*relevant, *sampled]
        if not candidates:
            continue

        # Считаем скор кандидатов.
        scores = {}
        for mid in candidates:
            cf_score = cb_score = pop_score = 0.0

            if algo:
                try:
                    cf_score = algo.predict(str(user_id), str(mid)).est / 5.0
                except Exception:
                    pass

            neg_score = 0.0
            if matrix is not None and weighted_positive and mid in id_to_idx:
                liked_idx = [id_to_idx[m] for m, _ in weighted_positive if m in id_to_idx]
                liked_w = np.asarray([w for m, w in weighted_positive if m in id_to_idx], dtype=np.float64)
                if liked_idx and np.sum(np.abs(liked_w)) > 1e-8:
                    liked_w = liked_w / np.sum(np.abs(liked_w))
                    profile = matrix[liked_idx].T.dot(liked_w).reshape(1, -1)
                    candidate_vec = matrix[id_to_idx[mid]].reshape(1, -1)
                    cb_score = float(cosine_similarity(profile, candidate_vec)[0][0])

            if matrix is not None and weighted_negative and mid in id_to_idx:
                neg_idx = [id_to_idx[m] for m, _ in weighted_negative if m in id_to_idx]
                neg_w = np.asarray([w for m, w in weighted_negative if m in id_to_idx], dtype=np.float64)
                if neg_idx and np.sum(np.abs(neg_w)) > 1e-8:
                    neg_w = neg_w / np.sum(np.abs(neg_w))
                    neg_profile = matrix[neg_idx].T.dot(neg_w).reshape(1, -1)
                    candidate_vec = matrix[id_to_idx[mid]].reshape(1, -1)
                    neg_score = float(cosine_similarity(neg_profile, candidate_vec)[0][0])

            if max_count > 0:
                pop_score = min(1.0, float(item_counts.get(mid, 0)) / max_count)

            if neg_score >= 0.63:
                scores[mid] = -1.0
                continue

            scores[mid] = 0.4 * cf_score + 0.4 * cb_score + 0.12 * pop_score - 0.60 * max(0.0, neg_score)

        recommended = sorted(scores, key=scores.get, reverse=True)
        users_data.append({"recommended": recommended, "relevant": relevant})

        if algo:
            for _, row in holdout_rows.iterrows():
                try:
                    pred = algo.predict(str(user_id), str(int(row["movie_id"]))).est
                    rmse_pairs.append((float(row["rating"]), pred))
                except Exception:
                    pass

    if not users_data:
        print("[eval] Не удалось сформировать данные для оценки.")
        _save_dummy_metrics()
        return

    result = average_metrics(users_data, k=K)
    if rmse_pairs:
        y_true, y_pred = zip(*rmse_pairs)
        result["rmse"] = round(rmse(list(y_true), list(y_pred)), 4)

    print("\n=== Результаты оценки ===")
    for key, val in result.items():
        print(f"  {key}: {val}")

    _save_metrics(result)
    print(f"\n[eval] Метрики сохранены: {MODELS_DIR / 'metrics.json'}")


def _save_metrics(data: dict) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    with open(MODELS_DIR / "metrics.json", "w") as f:
        json.dump(data, f, indent=2)


def _save_dummy_metrics() -> None:
    _save_metrics({
        f"precision_at_{K}": 0.0,
        f"recall_at_{K}": 0.0,
        f"ndcg_at_{K}": 0.0,
        "rmse": None,
    })


if __name__ == "__main__":
    evaluate()
