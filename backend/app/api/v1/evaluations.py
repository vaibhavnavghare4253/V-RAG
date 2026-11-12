from typing import Any, List
from fastapi import APIRouter, status
from sqlalchemy import desc, select

from app.api.deps import CurrentUserDep, DbDep
from app.models.trace import EvaluationRun

router = APIRouter(prefix="/evaluations", tags=["Evaluations & Benchmarks"])


@router.get("", response_model=List[dict])
async def list_evaluations(
    db: DbDep,
    current_user: CurrentUserDep,
) -> Any:
    """List historical evaluation runs across baselines (DocVQA, ChartQA, MMLongBench)."""
    stmt = select(EvaluationRun).order_by(desc(EvaluationRun.created_at)).limit(50)
    runs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "dataset_name": r.dataset_name,
            "baseline_name": r.baseline_name,
            "status": r.status,
            "sample_size": r.sample_size,
            "metrics": r.metrics,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]

