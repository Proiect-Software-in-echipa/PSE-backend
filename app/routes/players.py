from fastapi import APIRouter, Query
from typing import Optional

from app.models.transfer import PlayerInfo
from app.services import transfer_service

router = APIRouter(prefix="/players", tags=["Jucători"])


@router.get(
    "",
    response_model=list[PlayerInfo],
    summary="Listare jucători cu statistici",
)
def list_players(
    search: Optional[str] = Query(None, description="Caută după numele jucătorului"),
):
    return transfer_service.get_players(search)
