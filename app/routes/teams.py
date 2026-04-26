from fastapi import APIRouter, Query
from typing import Optional

from app.models.transfer import TeamInfo
from app.services import transfer_service

router = APIRouter(prefix="/teams", tags=["Echipe"])


@router.get(
    "",
    response_model=list[TeamInfo],
    summary="Listare echipe cu statistici de transfer",
)
def list_teams(
    search: Optional[str] = Query(None, description="Caută după numele echipei"),
):
    return transfer_service.get_teams(search)
