import hashlib
from typing import Any, Optional

from app.cache.cache_manager import cache
from app.models.transfer import Transfer
from app.services.probability_service import calculate_probability, count_sources
from app.services.s3_service import fetch_transfers_json

DEFAULT_RUMOR_STRENGTH = 5.0
TRANSFERS_CACHE_KEY = "store:transfers"
TRANSFERS_CACHE_TTL = 300


def _str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _fix_mojibake(text: str) -> str:
    """Repair text that was UTF-8 bytes decoded as Latin-1 (e.g. 'â' → '–', 'AraÃºjo' → 'Araújo')."""
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _stable_id(record_type_id: str) -> str:
    return hashlib.sha1(record_type_id.encode("utf-8")).hexdigest()


def _confidence_to_strength(raw: Any) -> float:
    if raw is None or raw == "":
        return DEFAULT_RUMOR_STRENGTH
    try:
        c = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_RUMOR_STRENGTH
    if c > 10:
        return round(min(10.0, c / 10.0), 2)
    return round(min(10.0, max(0.0, c)), 2)


def _record_to_transfer(raw: dict[str, Any]) -> Optional[Transfer]:
    player = _str(raw.get("player"))
    from_team = _str(raw.get("fromClub") or raw.get("from_club"))
    to_team = _str(raw.get("toClub") or raw.get("to_club"))
    if not player or not from_team or not to_team:
        return None

    sources_str = _str(raw.get("source") or raw.get("sources")) or "Unknown"
    source_count = count_sources(sources_str)

    status = _str(raw.get("status")) or "Rumor"
    is_confirmed = status.lower() == "confirmed"

    confidence_raw = raw.get("confidenceLevel", "")
    if is_confirmed:
        rumor_strength = 10.0
    else:
        rumor_strength = _confidence_to_strength(confidence_raw)

    confidence_level: Optional[int] = None
    if confidence_raw not in (None, ""):
        try:
            confidence_level = int(float(confidence_raw))
        except (TypeError, ValueError):
            pass
    if is_confirmed and confidence_level is None:
        confidence_level = 100

    prob, _ = calculate_probability(
        rumor_strength=rumor_strength,
        source_count=source_count,
        from_team=from_team,
        to_team=to_team,
        status=status,
    )

    record_type_id = _str(raw.get("recordTypeId")) or f"{player}|{from_team}|{to_team}"

    return Transfer(
        id=_stable_id(record_type_id),
        player=_fix_mojibake(player),
        from_team=_fix_mojibake(from_team),
        to_team=_fix_mojibake(to_team),
        sources=sources_str,
        rumor_strength=rumor_strength,
        probability=prob,
        source_count=source_count,
        status=status,
        confidence_level=confidence_level,
        fee_amount=_str(raw.get("feeAmount")) or None,
        url=_str(raw.get("url")) or None,
        raw_title=_fix_mojibake(_str(raw.get("rawTitle"))) or None,
        transfer_timestamp=_str(raw.get("timestamp")) or None,
    )


class TransferStore:
    def _load(self) -> list[Transfer]:
        cached = cache.get(TRANSFERS_CACHE_KEY)
        if cached is not None:
            return cached
        records = fetch_transfers_json()
        transfers = [t for r in records if (t := _record_to_transfer(r)) is not None]
        cache.set(TRANSFERS_CACHE_KEY, transfers, ttl=TRANSFERS_CACHE_TTL)
        return transfers

    def refresh(self) -> int:
        cache.delete(TRANSFERS_CACHE_KEY)
        return len(self._load())

    def get_all(self) -> list[Transfer]:
        return self._load()

    def get_by_id(self, transfer_id: str) -> Optional[Transfer]:
        for t in self._load():
            if t.id == transfer_id:
                return t
        return None

    def count(self) -> int:
        return len(self._load())

    def filter(
        self,
        player: Optional[str] = None,
        from_team: Optional[str] = None,
        to_team: Optional[str] = None,
        min_strength: Optional[float] = None,
        max_strength: Optional[float] = None,
        min_probability: Optional[float] = None,
        status: Optional[str] = None,
    ) -> list[Transfer]:
        transfers = self._load()

        if min_strength is not None:
            transfers = [t for t in transfers if t.rumor_strength >= min_strength]
        if max_strength is not None:
            transfers = [t for t in transfers if t.rumor_strength <= max_strength]
        if min_probability is not None:
            transfers = [t for t in transfers if t.probability >= min_probability]
        if player:
            q = player.lower()
            transfers = [t for t in transfers if q in t.player.lower()]
        if from_team:
            q = from_team.lower()
            transfers = [t for t in transfers if q in t.from_team.lower()]
        if to_team:
            q = to_team.lower()
            transfers = [t for t in transfers if q in t.to_team.lower()]
        if status:
            q = status.lower()
            transfers = [t for t in transfers if t.status.lower() == q]

        return transfers

    def get_top(self, limit: int = 10) -> list[Transfer]:
        return sorted(self._load(), key=lambda t: t.probability, reverse=True)[:limit]

    def get_trending(self, limit: int = 10) -> list[Transfer]:
        return sorted(self._load(), key=lambda t: t.source_count * t.rumor_strength, reverse=True)[:limit]

    def get_players(self) -> list[str]:
        return sorted({t.player for t in self._load()})

    def get_teams(self) -> list[str]:
        teams: set[str] = set()
        for t in self._load():
            teams.add(t.from_team)
            teams.add(t.to_team)
        return sorted(teams)


store = TransferStore()
