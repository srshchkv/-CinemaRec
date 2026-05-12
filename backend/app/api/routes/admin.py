from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.analytics import AdminStats, AnalyticsDashboard, ModelMetrics
from app.schemas.user import UserResponse
from app.analytics.tracker import get_admin_stats, get_analytics_dashboard
from app.auth.dependencies import get_current_admin
from app.models.user import User, UserRole

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return get_admin_stats(db)


@router.get("/analytics", response_model=AnalyticsDashboard)
def analytics_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return get_analytics_dashboard(db)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    users = db.query(User).filter(User.role == UserRole.user).limit(100).all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/metrics", response_model=ModelMetrics)
def model_metrics(_: User = Depends(get_current_admin)):
    """Returns evaluation metrics from the last ML training run."""
    import json
    from pathlib import Path
    metrics_path = Path(__file__).resolve().parents[4] / "ml" / "models" / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            data = json.load(f)
        return ModelMetrics(**{k: v for k, v in data.items() if v is not None or k == "rmse"})
    return ModelMetrics(precision_at_10=0.0, recall_at_10=0.0, ndcg_at_10=0.0)
