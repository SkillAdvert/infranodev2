"""Financial modelling API routes."""
from fastapi import APIRouter, HTTPException

from domain.financial.services import (
    FinancialModelRequest,
    FinancialModelResponse,
    run_financial_models,
)

router = APIRouter(prefix="/api", tags=["financial"])


@router.post("/financial-model", response_model=FinancialModelResponse)
async def calculate_financial_model(request: FinancialModelRequest) -> FinancialModelResponse:
    try:
        return run_financial_models(request)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc
