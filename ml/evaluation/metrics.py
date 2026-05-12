"""
Recommendation quality metrics.
    - Precision@K
    - Recall@K
    - NDCG@K
    - RMSE (for rating prediction)
"""
import math
import numpy as np
from typing import List


def precision_at_k(recommended: List[int], relevant: set[int], k: int) -> float:
    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / k if k > 0 else 0.0


def recall_at_k(recommended: List[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = recommended[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: List[int], relevant: set[int], k: int) -> float:
    top_k = recommended[:k]
    dcg = sum(
        1.0 / math.log2(i + 2)
        for i, item in enumerate(top_k)
        if item in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def rmse(y_true: List[float], y_pred: List[float]) -> float:
    if not y_true:
        return 0.0
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true))


def average_metrics(users_data: list[dict], k: int = 10) -> dict:
    """
    users_data: list of {recommended: [id,...], relevant: {id,...}}
    Returns mean Precision@K, Recall@K, NDCG@K.
    """
    p_vals, r_vals, n_vals = [], [], []
    for d in users_data:
        rec = d["recommended"]
        rel = d["relevant"]
        p_vals.append(precision_at_k(rec, rel, k))
        r_vals.append(recall_at_k(rec, rel, k))
        n_vals.append(ndcg_at_k(rec, rel, k))
    return {
        f"precision_at_{k}": round(float(np.mean(p_vals)), 4),
        f"recall_at_{k}": round(float(np.mean(r_vals)), 4),
        f"ndcg_at_{k}": round(float(np.mean(n_vals)), 4),
    }
