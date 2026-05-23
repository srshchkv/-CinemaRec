"""
Оффлайн-оценка рекомендательной системы.
Схема leave-one-out: скрываем последнюю оценку пользователя и измеряем качество.
Вычисляются метрики отдельно для SVD, TF-IDF.
Для гибрида перебираются 9 комбинаций весов, сохраняется лучшая по Precision@K.
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

# ── 9 вариантов весов для гибрида ─────────────────────────────
HYBRID_WEIGHTS = [
    {"name": "hybrid_cf050_cb030", "w_cf": 0.50, "w_cb": 0.30, "w_pop": 0.12, "w_click": 0.08, "neg_block": 0.62, "neg_penalty": 0.60},
    {"name": "hybrid_cf045_cb035", "w_cf": 0.45, "w_cb": 0.35, "w_pop": 0.12, "w_click": 0.08, "neg_block": 0.62, "neg_penalty": 0.60},
    {"name": "hybrid_cf040_cb040", "w_cf": 0.40, "w_cb": 0.40, "w_pop": 0.12, "w_click": 0.08, "neg_block": 0.62, "neg_penalty": 0.60},
    {"name": "hybrid_cf035_cb045", "w_cf": 0.35, "w_cb": 0.45, "w_pop": 0.12, "w_click": 0.08, "neg_block": 0.62, "neg_penalty": 0.60},
    {"name": "hybrid_cf030_cb050", "w_cf": 0.30, "w_cb": 0.50, "w_pop": 0.12, "w_click": 0.08, "neg_block": 0.62, "neg_penalty": 0.60},
    {"name": "hybrid_cf025_cb055", "w_cf": 0.25, "w_cb": 0.55, "w_pop": 0.12, "w_click": 0.08, "neg_block": 0.62, "neg_penalty": 0.60},
    {"name": "hybrid_cf020_cb060", "w_cf": 0.20, "w_cb": 0.60, "w_pop": 0.12, "w_click": 0.08, "neg_block": 0.62, "neg_penalty": 0.60},
]


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


def _prepare_user_data(eligible_users, ratings, movie_ids, all_movie_ids):
    """
    Подготавливает данные по пользователям: разбиение train/holdout,
    взвешенные положительные/отрицательные преференции.
    Возвращает список dict-ов для каждого пользователя.
    """
    user_data_list = []

    for user_id in eligible_users:
        sort_col = "timestamp" if "timestamp" in ratings.columns else "movie_id"
        user_ratings = ratings[ratings["user_id"] == user_id].sort_values(sort_col)
        positive = user_ratings[user_ratings["rating"] >= 4.0]
        if len(user_ratings) < MIN_RATINGS_PER_USER or len(positive) < 4:
            continue

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

        user_data_list.append({
            "user_id": user_id,
            "relevant": relevant,
            "candidates": candidates,
            "weighted_positive": weighted_positive,
            "weighted_negative": weighted_negative,
            "holdout_rows": holdout_rows,
        })

    return user_data_list


def _score_cf(candidates, user_id, algo):
    """Только CF (SVD) скоры."""
    scores = {}
    for mid in candidates:
        try:
            scores[mid] = algo.predict(str(user_id), str(mid)).est / 5.0
        except Exception:
            scores[mid] = 0.0
    return scores


def _score_cb(candidates, matrix, id_to_idx, weighted_positive):
    """Только CB (TF-IDF) скоры на основе положительных преференций."""
    scores = {}
    if matrix is None or not weighted_positive:
        return {mid: 0.0 for mid in candidates}
    liked_idx = [id_to_idx.get(m) for m, _ in weighted_positive if m in id_to_idx]
    liked_w = np.asarray([w for m, w in weighted_positive if m in id_to_idx], dtype=np.float64)
    if not liked_idx or np.sum(np.abs(liked_w)) < 1e-8:
        return {mid: 0.0 for mid in candidates}
    liked_w = liked_w / np.sum(np.abs(liked_w))
    profile = matrix[liked_idx].T.dot(liked_w).reshape(1, -1)
    for mid in candidates:
        if mid in id_to_idx:
            vec = matrix[id_to_idx[mid]].reshape(1, -1)
            scores[mid] = float(cosine_similarity(profile, vec)[0][0])
        else:
            scores[mid] = 0.0
    return scores


def _score_hybrid(candidates, user_id, algo, matrix, id_to_idx,
                  weighted_positive, weighted_negative, item_counts, max_count,
                  weights):
    """Гибридные скоры с заданными весами."""
    cf_scores = {}
    if algo:
        cf_scores = _score_cf(candidates, user_id, algo)

    cb_scores = _score_cb(candidates, matrix, id_to_idx, weighted_positive)

    neg_scores = {}
    if matrix is not None and weighted_negative:
        neg_idx = [id_to_idx.get(m) for m, _ in weighted_negative if m in id_to_idx]
        neg_w = np.asarray([w for m, w in weighted_negative if m in id_to_idx], dtype=np.float64)
        if neg_idx and np.sum(np.abs(neg_w)) > 1e-8:
            neg_w = neg_w / np.sum(np.abs(neg_w))
            neg_profile = matrix[neg_idx].T.dot(neg_w).reshape(1, -1)
            for mid in candidates:
                if mid in id_to_idx:
                    vec = matrix[id_to_idx[mid]].reshape(1, -1)
                    neg_scores[mid] = float(cosine_similarity(neg_profile, vec)[0][0])

    scores = {}
    for mid in candidates:
        cf = cf_scores.get(mid, 0.0)
        cb = cb_scores.get(mid, 0.0)
        pop = min(1.0, float(item_counts.get(mid, 0)) / max_count) if max_count > 0 else 0.0
        neg = max(0.0, neg_scores.get(mid, 0.0))

        if neg >= weights["neg_block"]:
            scores[mid] = -1.0
            continue

        scores[mid] = (weights["w_cf"] * cf + weights["w_cb"] * cb + weights["w_pop"] * pop
                       - weights["neg_penalty"] * neg)
    return scores


def _evaluate_model(user_data_list, scorer_fn, model_name, algo=None):
    """
    Универсальная функция оценки для любой модели.
    scorer_fn принимает (candidates, user_id, ...) и возвращает dict[mid -> score].
    """
    users_data = []
    rmse_pairs = []

    for ud in user_data_list:
        scores = scorer_fn(ud["candidates"], ud["user_id"])
        recommended = sorted(scores, key=scores.get, reverse=True)
        users_data.append({"recommended": recommended, "relevant": ud["relevant"]})

        if algo and model_name in ("cf", "hybrid"):
            for _, row in ud["holdout_rows"].iterrows():
                try:
                    pred = algo.predict(str(ud["user_id"]), str(int(row["movie_id"]))).est
                    rmse_pairs.append((float(row["rating"]), pred))
                except Exception:
                    pass

    if not users_data:
        return None

    result = average_metrics(users_data, k=K)
    if rmse_pairs:
        y_true, y_pred = zip(*rmse_pairs)
        result["rmse"] = round(rmse(list(y_true), list(y_pred)), 4)

    return result


def _evaluate_cf(user_data_list, algo):
    """Оценка только коллаборативной фильтрации (SVD)."""
    def scorer(candidates, user_id):
        return _score_cf(candidates, user_id, algo)
    return _evaluate_model(user_data_list, scorer, "cf", algo)


def _evaluate_cb(user_data_list, matrix, id_to_idx):
    """Оценка только контентной фильтрации (TF-IDF)."""
    def scorer(candidates, user_id):
        weighted_positive = next(
            (ud["weighted_positive"] for ud in user_data_list if ud["user_id"] == user_id),
            []
        )
        return _score_cb(candidates, matrix, id_to_idx, weighted_positive)
    return _evaluate_model(user_data_list, scorer, "cb")


def _evaluate_hybrid(user_data_list, algo, matrix, id_to_idx, item_counts, max_count, weights):
    """Оценка гибридной модели с конкретными весами."""
    def scorer(candidates, user_id):
        ud = next(u for u in user_data_list if u["user_id"] == user_id)
        return _score_hybrid(
            candidates, user_id, algo, matrix, id_to_idx,
            ud["weighted_positive"], ud["weighted_negative"],
            item_counts, max_count, weights
        )
    return _evaluate_model(user_data_list, scorer, "hybrid", algo)


# ═══════════════════════════════════════════════════════════════

def _save_metrics(data: dict) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    with open(MODELS_DIR / "metrics.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _save_dummy_metrics() -> None:
    _save_metrics({
        f"precision_at_{K}": 0.0,
        f"recall_at_{K}": 0.0,
        f"ndcg_at_{K}": 0.0,
        "rmse": None,
    })


def evaluate():
    ratings = _load_ratings()
    matrix, movie_ids, id_to_idx, algo = _load_models()

    if matrix is None and algo is None:
        print("[eval] Модели не найдены в ml/models/ — оценка пропущена.")
        print("       Сначала запустите обучение через ml/main.py.")
        return

    if len(ratings) < MIN_RATINGS_PER_USER * 5:
        print("[eval] Недостаточно оценок в БД, запускаю оценку на синтетических данных…")
        from ml.svd.collaborative_model import generate_synthetic_ratings
        try:
            from ml.preprocessing.load_data import load_movies
            df_movies = load_movies()
            ratings = generate_synthetic_ratings(df_movies, n_users=100, ratings_per_user=500)
        except Exception as e:
            print(f"[eval] Не удалось сгенерировать синтетические оценки: {e}")
            _save_dummy_metrics()
            return

    if movie_ids:
        ratings = ratings[ratings["movie_id"].isin(set(movie_ids))]

    item_counts = ratings["movie_id"].value_counts()
    max_count = int(item_counts.max()) if len(item_counts) else 1

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
    user_data_list = _prepare_user_data(eligible, ratings, movie_ids, all_movie_ids)
    if not user_data_list:
        print("[eval] Не удалось сформировать данные для оценки.")
        _save_dummy_metrics()
        return

    # ── 1. CF (SVD) ────────────────────────────────────────────
    result_cf = None
    if algo:
        print("\n--- Оценка коллаборативной модели (SVD) ---")
        result_cf = _evaluate_cf(user_data_list, algo)
        if result_cf:
            print(f"  CF Precision@{K}: {result_cf.get(f'precision_at_{K}')}")
            print(f"  CF Recall@{K}:    {result_cf.get(f'recall_at_{K}')}")
            print(f"  CF RMSE:          {result_cf.get('rmse')}")

    # ── 2. CB (TF-IDF) ─────────────────────────────────────────
    result_cb = None
    if matrix is not None:
        print("\n--- Оценка контентной модели (TF-IDF) ---")
        result_cb = _evaluate_cb(user_data_list, matrix, id_to_idx)
        if result_cb:
            print(f"  CB Precision@{K}: {result_cb.get(f'precision_at_{K}')}")
            print(f"  CB Recall@{K}:    {result_cb.get(f'recall_at_{K}')}")

    # ── 3. Гибрид — перебор 7 весов, сохранение лучшего ───────
    print("\n--- Перебор 7 комбинаций весов гибридной модели ---")
    best_precision = -1.0
    best_weights = None
    best_result = None

    for w in HYBRID_WEIGHTS:
        result_h = _evaluate_hybrid(
            user_data_list, algo, matrix, id_to_idx,
            item_counts, max_count, w
        )
        if result_h is None:
            continue
        prec = result_h.get(f"precision_at_{K}", 0.0)
        print(f"  cf={w['w_cf']:.2f} cb={w['w_cb']:.2f}  →  Precision@{K}={prec:.4f}  Recall@{K}={result_h.get(f'recall_at_{K}'):.4f}  NDCG@{K}={result_h.get(f'ndcg_at_{K}'):.4f}")
        if prec > best_precision:
            best_precision = prec
            best_weights = w
            best_result = result_h

    # ── Формируем итоговый вывод ───────────────────────────────
    print("\n" + "=" * 55)
    print("  ИТОГОВЫЕ РЕЗУЛЬТАТЫ ОЦЕНКИ")
    print("=" * 55)

    if result_cf:
        print(f"\n--- CF (SVD) ---")
        for k, v in result_cf.items():
            print(f"  {k}: {v}")

    if result_cb:
        print(f"\n--- CB (TF-IDF) ---")
        for k, v in result_cb.items():
            print(f"  {k}: {v}")

    if best_result and best_weights:
        print(f"\n--- Гибрид (лучший) ---")
        print(f"  Лучшие веса: cf={best_weights['w_cf']}, cb={best_weights['w_cb']}, pop={best_weights['w_pop']}")
        for k, v in best_result.items():
            print(f"  {k}: {v}")

        best_result["best_weights"] = {
            "w_cf": best_weights["w_cf"],
            "w_cb": best_weights["w_cb"],
            "w_pop": best_weights["w_pop"],
        }

    # Сохраняем только: CF, CB и лучший гибрид
    final = {}
    if result_cf:
        final["cf_svd"] = result_cf
    if result_cb:
        final["cb_tfidf"] = result_cb
    if best_result:
        final["hybrid_best"] = best_result

    _save_metrics(final)
    print(f"\n[eval] Метрики сохранены: {MODELS_DIR / 'metrics.json'}")


if __name__ == "__main__":
    evaluate()
