from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone
import uuid


class TransferBase(BaseModel):
    player: str = Field(..., min_length=1)
    from_team: str = Field(..., min_length=1)
    to_team: str = Field(..., min_length=1)
    sources: str = Field(...)
    rumor_strength: float = Field(..., ge=0.0, le=10.0)

    @field_validator("rumor_strength", mode="before")
    @classmethod
    def round_strength(cls, v: float) -> float:
        return round(float(v), 2)

    @field_validator("player", "from_team", "to_team", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class Transfer(TransferBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    source_count: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="Rumor")
    rumor_share: Optional[float] = Field(None, ge=0.0, le=100.0)
    confidence_level: Optional[int] = Field(None, ge=0, le=100)
    fee_amount: Optional[str] = None
    url: Optional[str] = None
    raw_title: Optional[str] = None
    transfer_timestamp: Optional[str] = None

    model_config = {"from_attributes": True}


class TransferDetail(Transfer):
    probability_breakdown: dict = Field(default_factory=dict)


class TransferFilter(BaseModel):
    player: Optional[str] = None
    from_team: Optional[str] = None
    to_team: Optional[str] = None
    min_strength: Optional[float] = Field(None, ge=0.0, le=10.0)
    max_strength: Optional[float] = Field(None, ge=0.0, le=10.0)
    min_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = None

    model_config = {"extra": "ignore"}


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[Transfer]


class ProbabilityResponse(BaseModel):
    transfer_id: str
    player: str
    from_team: str
    to_team: str
    probability: float
    confidence_label: str
    breakdown: dict


class PlayerInfo(BaseModel):
    name: str
    transfer_count: int
    teams: list[str]
    avg_rumor_strength: float


class TeamInfo(BaseModel):
    name: str
    incoming: int
    outgoing: int
    avg_rumor_strength: float
    top_targets: list[str]
