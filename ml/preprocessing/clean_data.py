"""Clean and prepare movie data for ML pipeline."""
import pandas as pd


def build_text_field(df: pd.DataFrame) -> pd.Series:
    """
    Combined text for TF-IDF / sentence-transformers:
        title + genres + keywords + overview + language + year
    """
    def row_to_text(row) -> str:
        parts = []
        if pd.notna(row.get("title")):
            parts.append(str(row["title"]))
        if pd.notna(row.get("genres")):
            parts.append(str(row["genres"]).replace(",", " "))
        if pd.notna(row.get("keywords")):
            parts.append(str(row["keywords"]).replace(",", " "))
        if pd.notna(row.get("overview")):
            parts.append(str(row["overview"]))
        if pd.notna(row.get("original_language")):
            parts.append(str(row["original_language"]))
        if pd.notna(row.get("year")):
            parts.append(str(int(row["year"])))
        return " ".join(parts)

    return df.apply(row_to_text, axis=1)


def clean_genres(genres_str) -> list[str]:
    if pd.isna(genres_str) or not genres_str:
        return []
    return [g.strip() for g in str(genres_str).split(",") if g.strip()]


def clean_keywords(kw_str) -> list[str]:
    if pd.isna(kw_str) or not kw_str:
        return []
    return [k.strip() for k in str(kw_str).split(",") if k.strip()]


def filter_quality(df: pd.DataFrame, min_votes: int = 10) -> pd.DataFrame:
    filtered = df[df["vote_count"] >= min_votes].copy()
    print(f"[clean] {len(filtered)} movies after quality filter (min_votes={min_votes})")
    return filtered
