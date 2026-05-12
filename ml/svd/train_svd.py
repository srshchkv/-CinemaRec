"""
Обучение SVD и сохранение в `ml/models/`.
Вызывается из `ml/main.py` и получает `movies_df`, чтобы не читать CSV повторно.
Если в БД недостаточно оценок, используется синтетический датасет.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from ml.svd.collaborative_model import (
    load_ratings_from_db,
    generate_synthetic_ratings,
    train_svd,
    save_model,
)

MIN_RATINGS = 30


def run(movies_df: pd.DataFrame = None):
    """
    Обучает SVD. `movies_df` передается из `ml/main.py`,
    чтобы сгенерировать синтетические оценки без повторного чтения CSV.
    """
    ratings_df = pd.DataFrame(columns=["user_id", "movie_id", "rating"])

    # Сначала пробуем реальные оценки из БД.
    ratings_df = load_ratings_from_db()

    # Если данных мало, переходим на синтетические оценки.
    if len(ratings_df) < MIN_RATINGS:
        if movies_df is None or len(movies_df) == 0:
            print("[svd] Нет `movies_df`, а БД пуста — обучение SVD невозможно.")
            return None
        print(f"[svd] В БД только {len(ratings_df)} оценок → генерирую синтетические из CSV…")
        ratings_df = generate_synthetic_ratings(movies_df, n_users=100, ratings_per_user=500)

    algo, rmse_val = train_svd(ratings_df)
    save_model(algo)
    return rmse_val


if __name__ == "__main__":
    # Запуск в standalone-режиме: читаем CSV вручную.
    from ml.preprocessing.load_data import load_movies
    df = load_movies()
    run(df)
