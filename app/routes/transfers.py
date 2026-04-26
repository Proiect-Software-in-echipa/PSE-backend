from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.models.transfer import (
    Transfer,
    PaginatedResponse,
    TransferDetail,
    TransferFilter,
    ProbabilityResponse,
)
from app.services import transfer_service

router = APIRouter(prefix="/transfers", tags=["Transferuri"])


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="Listare transferuri cu filtre și paginare",
)
def list_transfers(
    player: Optional[str] = Query(None, description="Filtrare după numele jucătorului"),
    from_team: Optional[str] = Query(None, description="Filtrare după echipa de origine"),
    to_team: Optional[str] = Query(None, description="Filtrare după echipa destinație"),
    min_strength: Optional[float] = Query(None, ge=1.0, le=10.0),
    max_strength: Optional[float] = Query(None, ge=1.0, le=10.0),
    min_probability: Optional[float] = Query(None, ge=0.0, le=1.0),
    status: Optional[str] = Query(None, description="Filtrare după status: Rumor / Confirmed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("probability", description="Câmpul de sortare"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    filters = TransferFilter(
        player=player,
        from_team=from_team,
        to_team=to_team,
        min_strength=min_strength,
        max_strength=max_strength,
        min_probability=min_probability,
        status=status,
    )
    return transfer_service.list_transfers(filters, page, page_size, sort_by, order)


@router.get(
    "/all",
    response_model=list[Transfer],
    summary="Toate transferurile (fără paginare)",
)
def all_transfers():
    return transfer_service.get_all_transfers()


@router.post(
    "/refresh",
    summary="Re-încarcă datele din S3 (invalidează cache-ul)",
)
def refresh_transfers():
    count = transfer_service.refresh_from_source()
    return {"status": "ok", "transfers_loaded": count}


@router.get(
    "/top",
    response_model=list[Transfer],
    summary="Top transferuri după probabilitate",
)
def top_transfers(limit: int = Query(10, ge=1, le=50)):
    return transfer_service.get_top_transfers(limit)


@router.get(
    "/trending",
    response_model=list[Transfer],
    summary="Transferuri trending (surse × putere zvon)",
)
def trending_transfers(limit: int = Query(10, ge=1, le=50)):
    return transfer_service.get_trending_transfers(limit)


@router.get(
    "/{transfer_id}",
    response_model=TransferDetail,
    summary="Detalii transfer",
)
def get_transfer(transfer_id: str):
    transfer = transfer_service.get_transfer_detail(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transferul nu a fost găsit.")
    return transfer


@router.get(
    "/{transfer_id}/probability",
    response_model=ProbabilityResponse,
    summary="Estimare probabilitate transfer",
)
def get_probability(transfer_id: str):
    result = transfer_service.estimate_probability(transfer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Transferul nu a fost găsit.")
    return result
