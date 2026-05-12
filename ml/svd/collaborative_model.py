"""
Surprise SVD collaborative filtering model.

If the application DB has ratings (after seeding) → uses them.
Otherwise → generates synthetic ratings from the movie CSV directly,
so this step always succeeds even before the backend is set up.
"""
import math
import pickle
import random
import os
from pathlib import Path

import numpy as np
import pandas as pd
from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split as surprise_split
from sqlalchemy import create_engine, text

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
ROOT = Path(__file__).resolve().parent.parent.parent

GENRE_PROFILES = {
    0: {"Action": 0.7, "Thriller": 0.9, "Crime": 0.45, "Drama": 0.6, "Romance": 0.3, "Science Fiction": 0.6},
    1: {"Drama": 0.9, "Romance": 0.7, "Family": 0.6, "History": 0.5, "Action": 0.2},
    2: {"Science Fiction": 0.95, "Adventure": 0.7, "Action": 0.6, "Fantasy": 0.7},
    3: {"Comedy": 0.9, "Romance": 0.6, "Family": 0.5, "Drama": 0.3},
    4: {"Horror": 0.95, "Thriller": 0.8, "Mystery": 0.6, "Crime": 0.5},
    5: {"Animation": 0.9, "Family": 0.8, "Comedy": 0.6, "Adventure": 0.7},
    6: {"Documentary": 0.9, "History": 0.7, "Drama": 0.6},
    7: {"Thriller": 0.9, "Mystery": 0.8, "Crime": 0.7, "Action": 0.5},
}


def _resolve_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    backend_env = ROOT / "backend" / ".env"
    if backend_env.exists():
        for raw_line in backend_env.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "DATABASE_URL":
                return value.strip().strip("'").strip('"')

    return f"sqlite:///{(ROOT / 'backend' / 'data' / 'cinemadb.db').as_posix()}"


def load_ratings_from_db(db_url: str | None = None) -> pd.DataFrame:
    try:
        engine = create_engine(db_url or _resolve_database_url(), pool_pre_ping=True)
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT user_id, movie_id, rating FROM ratings"), conn)
        print(f"[svd] Loaded {len(df)} ratings from DB")
        return df
    except Exception as e:
        print(f"[svd] Could not load DB ratings: {e}")
        return pd.DataFrame(columns=["user_id", "movie_id", "rating"])


def generate_synthetic_ratings(movies_df: pd.DataFrame, n_users: int = 100, ratings_per_user: int = 500) -> pd.DataFrame:
    """
    Generate synthetic user-movie ratings from movie metadata.
    Used when the application DB has no ratings yet.
    Produces a realistic user-movie matrix for SVD training.
    """
    print(f"[svd] Generating synthetic ratings for {n_users} users from {len(movies_df)} movies…")

    # Work with top movies by popularity for speed
    df = movies_df.copy()
    df = df[df["vote_count"] >= 20].dropna(subset=["id"])
    df["id"] = df["id"].astype(int)
    df = df.sort_values("popularity", ascending=False).head(15_000)

    movie_ids = df["id"].tolist()
    vote_avgs = dict(zip(df["id"], df["vote_average"].fillna(5.0)))
    genres_map = dict(zip(df["id"], df["genres"].fillna("")))

    rng = random.Random(42)
    np.random.seed(42)

    records = []
    for user_id in range(1, n_users + 1):
        profile = GENRE_PROFILES[user_id % len(GENRE_PROFILES)]
        n_ratings = min(ratings_per_user, len(movie_ids))
        sample_size = min(n_ratings * 4, len(movie_ids))
        sample = rng.sample(movie_ids, sample_size)

        seen = set()
        count = 0
        for mid in sample:
            if count >= n_ratings:
                break
            if mid in seen:
                continue
            seen.add(mid)
            count += 1

            genres_str = genres_map.get(mid, "")
            movie_genres = [g.strip() for g in genres_str.split(",") if g.strip()]
            pref = max((profile.get(g, 0.0) for g in movie_genres), default=0.1)

            base = (vote_avgs.get(mid, 5.0) / 10.0) * 5.0
            bias = (pref - 0.5) * 1.8
            noise = rng.gauss(0, 0.25)
            raw = base + bias + noise
            rating = round(max(0.5, min(5.0, raw)) * 2) / 2  # snap to 0.5 steps

            records.append({"user_id": user_id, "movie_id": mid, "rating": rating})

    df_out = pd.DataFrame(records)
    print(f"[svd] Generated {len(df_out)} synthetic ratings")
    return df_out


def train_svd(ratings_df: pd.DataFrame, n_factors: int = 100, n_epochs: int = 20):
    if len(ratings_df) < 10:
        raise ValueError(f"Not enough ratings to train SVD (got {len(ratings_df)}, need ≥10)")

    reader = Reader(rating_scale=(0.5, 5.0))
    data = Dataset.load_from_df(ratings_df[["user_id", "movie_id", "rating"]], reader)

    # Use smaller test split if dataset is small
    test_size = min(0.15, max(0.05, 50 / len(ratings_df)))
    trainset, testset = surprise_split(data, test_size=test_size, random_state=42)

    configs = [
        {"n_factors": n_factors, "n_epochs": n_epochs, "lr_all": 0.005, "reg_all": 0.02},
        {"n_factors": 120, "n_epochs": 30, "lr_all": 0.004, "reg_all": 0.03},
        {"n_factors": 80, "n_epochs": 35, "lr_all": 0.0035, "reg_all": 0.04},
        {"n_factors": 140, "n_epochs": 25, "lr_all": 0.0045, "reg_all": 0.025},
    ]

    best_algo = None
    best_rmse = float("inf")
    best_cfg = None

    for cfg in configs:
        algo = SVD(**cfg, random_state=42)
        algo.fit(trainset)
        predictions = algo.test(testset)
        rmse_val = _compute_rmse(predictions)
        print(
            "[svd] Trial"
            f" factors={cfg['n_factors']}"
            f" epochs={cfg['n_epochs']}"
            f" lr={cfg['lr_all']}"
            f" reg={cfg['reg_all']}"
            f" rmse={rmse_val:.4f}"
        )
        if rmse_val < best_rmse:
            best_rmse = rmse_val
            best_algo = algo
            best_cfg = cfg

    print(
        "[svd] Best config"
        f" factors={best_cfg['n_factors']}"
        f" epochs={best_cfg['n_epochs']}"
        f" lr={best_cfg['lr_all']}"
        f" reg={best_cfg['reg_all']}"
        f" rmse={best_rmse:.4f}"
    )
    return best_algo, best_rmse


def _compute_rmse(predictions) -> float:
    errors = [(p.r_ui - p.est) ** 2 for p in predictions]
    return math.sqrt(sum(errors) / len(errors)) if errors else 0.0


def save_model(algo: SVD) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    path = MODELS_DIR / "svd_model.pkl"
    with open(path, "wb") as f:
        pickle.dump(algo, f)
    print(f"[svd] Model saved → {path}")
