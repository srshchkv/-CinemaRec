"""Загрузка и базовая валидация CSV с фильмами."""
import pandas as pd
from pathlib import Path

CSV_CANDIDATES = [
    Path(__file__).parent.parent.parent / "data_movies_ВКР2.csv",
    Path(__file__).parent.parent.parent / "data_movies_ВКР.csv",
]


def resolve_csv_path() -> Path:
    for candidate in CSV_CANDIDATES:
        if candidate.exists():
            return candidate
    return CSV_CANDIDATES[0]


def load_movies(csv_path: Path | None = None) -> pd.DataFrame:
    csv_path = csv_path or resolve_csv_path()
    df = pd.read_csv(csv_path, low_memory=False)

    required = {"id", "title", "vote_average", "vote_count", "popularity", "genres", "keywords", "overview", "year"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"В CSV отсутствуют обязательные колонки: {missing}")

    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce").fillna(0.0)
    df["vote_count"] = pd.to_numeric(df["vote_count"], errors="coerce").fillna(0).astype(int)
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce").fillna(0.0)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = df.dropna(subset=["id", "title"])
    df["id"] = df["id"].astype(int)

    print(f"[load] Загружено {len(df)} фильмов из {csv_path.name}")
    return df
