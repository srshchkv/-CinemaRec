"""
Build and save TF-IDF content similarity matrix.
Optionally use SentenceTransformers MiniLM (set USE_SENTENCE_TRANSFORMERS=true).
"""
import os
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.sparse import save_npz
from sklearn.feature_extraction.text import TfidfVectorizer

MODELS_DIR = Path(__file__).parent.parent / "models"
USE_ST = os.getenv("USE_SENTENCE_TRANSFORMERS", "false").lower() == "true"


def build_tfidf(texts: list[str], movie_ids: list[int]) -> None:
    print(f"[tfidf] Building TF-IDF matrix for {len(texts)} movies...")
    vectorizer = TfidfVectorizer(
        max_features=15_000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        strip_accents="unicode",
        analyzer="word",
        token_pattern=r"\w{2,}",
    )
    matrix = vectorizer.fit_transform(texts)
    print(f"[tfidf] Matrix shape: {matrix.shape}")

    MODELS_DIR.mkdir(exist_ok=True)
    save_npz(MODELS_DIR / "tfidf_matrix.npz", matrix)
    with open(MODELS_DIR / "tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(MODELS_DIR / "movie_ids.pkl", "wb") as f:
        pickle.dump(movie_ids, f)
    print(f"[tfidf] Saved to {MODELS_DIR}")


def build_sentence_embeddings(texts: list[str], movie_ids: list[int]) -> None:
    from sentence_transformers import SentenceTransformer
    print("[minilm] Loading SentenceTransformer (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"[minilm] Encoding {len(texts)} texts...")
    embeddings = model.encode(texts, batch_size=128, show_progress_bar=True, normalize_embeddings=True)

    MODELS_DIR.mkdir(exist_ok=True)
    np.save(MODELS_DIR / "embeddings.npy", embeddings)
    with open(MODELS_DIR / "movie_ids.pkl", "wb") as f:
        pickle.dump(movie_ids, f)
    print(f"[minilm] Saved embeddings shape: {embeddings.shape}")


def build_embeddings(df: pd.DataFrame, text_col: str = "combined_text") -> None:
    texts = df[text_col].tolist()
    movie_ids = df["id"].tolist()

    if USE_ST:
        build_sentence_embeddings(texts, movie_ids)
    else:
        build_tfidf(texts, movie_ids)
