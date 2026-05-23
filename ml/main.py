"""
ML-пайплайн CinemaRec.
Запуск из корня: python -m ml.main
Или из директории ml/: python main.py
"""
import sys
from pathlib import Path

# Добавляем пути проекта и backend в sys.path
ROOT = Path(__file__).resolve().parent.parent   # cinemarec/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from ml.preprocessing.load_data import load_movies
from ml.preprocessing.clean_data import build_text_field, filter_quality
from ml.embeddings.content_embeddings import build_embeddings
from ml.svd.train_svd import run as train_svd_run
from ml.evaluation.evaluate import evaluate


def main():
    print("=" * 55)
    print("  ML-пайплайн CinemaRec")
    print("=" * 55)

    # ── Шаг 1: Загрузка и очистка данных ──────────────────────
    print("\n--- Шаг 1: Загрузка и очистка данных ---")
    df = load_movies()
    df = filter_quality(df, min_votes=100)
    df["combined_text"] = build_text_field(df)
    print(f"[main] Данные готовы: {len(df)} фильмов | пример текста: {df['combined_text'].iloc[0][:70]}…")

    # ── Шаг 2: Контентные эмбеддинги (TF-IDF) ────────────────
    print("\n--- Шаг 2: Контентные эмбеддинги (TF-IDF) ---")
    try:
        build_embeddings(df)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось построить контентные эмбеддинги: {e}")
        print("        Backend переключится на рекомендации только по популярности.")

    # ── Шаг 3: Коллаборативная фильтрация (SVD) ──────────────
    print("\n--- Шаг 3: Коллаборативная фильтрация (SVD) ---")
    try:
        rmse_val = train_svd_run(df)
        if rmse_val is not None:
            print(f"[main] RMSE модели SVD: {rmse_val:.4f}")
    except Exception as e:
        print(f"[ОШИБКА] Ошибка обучения SVD: {e}")
        print("        Backend пропустит коллаборативную составляющую.")

    # ── Шаг 4: Оценка качества ───────────────────────────────
    print("\n--- Шаг 4: Оценка качества ---")
    print("       Оцениваются: SVD (CF), TF-IDF (CB), гибрид (перебор 7 весов → лучший)")
    try:
        evaluate()
    except Exception as e:
        print(f"[ПРЕДУПРЕЖДЕНИЕ] Оценка качества завершилась с ошибкой: {e}")

    print("\n" + "=" * 55)
    print("  Обучение завершено. Модели сохранены в ml/models/")
    print("=" * 55)


if __name__ == "__main__":
    main()
