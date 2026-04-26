import math
from typing import Optional

from app.models.transfer import (
    Transfer,
    TransferDetail,
    TransferFilter,
    PaginatedResponse,
    ProbabilityResponse,
    PlayerInfo,
    TeamInfo,
)
from app.services.transfer_store import store
from app.services.probability_service import (
    calculate_probability,
    get_confidence_label,
)
from app.cache.cache_manager import cache


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int]:
    total = len(items)
    start = (page - 1) * page_size
    return items[start : start + page_size], total


def _assign_rumor_shares(transfers: list[Transfer]) -> list[Transfer]:
    if not transfers:
        return transfers
    players_in_result = {t.player for t in transfers}
    player_totals: dict[str, float] = {}
    for t in store.get_all():
        if t.player in players_in_result:
            player_totals[t.player] = player_totals.get(t.player, 0.0) + t.probability
    result = []
    for t in transfers:
        total = player_totals.get(t.player, 0.0)
        share = round(t.probability / total * 100, 1) if total > 0 else 0.0
        result.append(t.model_copy(update={"rumor_share": share}))
    return result


def list_transfers(
    filters: TransferFilter,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "probability",
    order: str = "desc",
) -> PaginatedResponse:
    cache_key = f"list:{filters.model_dump_json()}:{page}:{page_size}:{sort_by}:{order}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    results = store.filter(
        player=filters.player,
        from_team=filters.from_team,
        to_team=filters.to_team,
        min_strength=filters.min_strength,
        max_strength=filters.max_strength,
        min_probability=filters.min_probability,
        status=filters.status,
    )

    valid_sort_fields = {"probability", "rumor_strength", "source_count", "player", "from_team", "to_team"}
    if sort_by not in valid_sort_fields:
        sort_by = "probability"
    reverse = order.lower() != "asc"
    results = sorted(results, key=lambda t: getattr(t, sort_by), reverse=reverse)
    results = _assign_rumor_shares(results)

    page_items, total = _paginate(results, page, page_size)
    pages = math.ceil(total / page_size) if page_size else 1

    response = PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=page_items,
    )
    cache.set(cache_key, response, ttl=60)
    return response


def get_transfer_detail(transfer_id: str) -> Optional[TransferDetail]:
    t = store.get_by_id(transfer_id)
    if not t:
        return None
    _, breakdown = calculate_probability(
        rumor_strength=t.rumor_strength,
        source_count=t.source_count,
        from_team=t.from_team,
        to_team=t.to_team,
        status=t.status,
    )
    return TransferDetail(**t.model_dump(), probability_breakdown=breakdown)


def estimate_probability(transfer_id: str) -> Optional[ProbabilityResponse]:
    t = store.get_by_id(transfer_id)
    if not t:
        return None
    prob, breakdown = calculate_probability(
        rumor_strength=t.rumor_strength,
        source_count=t.source_count,
        from_team=t.from_team,
        to_team=t.to_team,
        status=t.status,
    )
    return ProbabilityResponse(
        transfer_id=t.id,
        player=t.player,
        from_team=t.from_team,
        to_team=t.to_team,
        probability=prob,
        confidence_label=get_confidence_label(prob),
        breakdown=breakdown,
    )


def get_all_transfers() -> list[Transfer]:
    cache_key = "all:transfers"
    cached = cache.get(cache_key)
    if cached:
        return cached
    result = _assign_rumor_shares(store.get_all())
    cache.set(cache_key, result, ttl=120)
    return result


def refresh_from_source() -> int:
    count = store.refresh()
    cache.clear()
    return count


def get_top_transfers(limit: int = 10) -> list[Transfer]:
    cache_key = f"top:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    result = _assign_rumor_shares(store.get_top(limit))
    cache.set(cache_key, result, ttl=120)
    return result


def get_trending_transfers(limit: int = 10) -> list[Transfer]:
    cache_key = f"trending:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    result = _assign_rumor_shares(store.get_trending(limit))
    cache.set(cache_key, result, ttl=120)
    return result


def get_players(search: Optional[str] = None) -> list[PlayerInfo]:
    all_transfers = store.get_all()
    player_map: dict[str, list[Transfer]] = {}
    for t in all_transfers:
        player_map.setdefault(t.player, []).append(t)
    results = []
    for name, transfers in player_map.items():
        if search and search.lower() not in name.lower():
            continue
        teams = list({t.from_team for t in transfers} | {t.to_team for t in transfers})
        avg_strength = round(sum(t.rumor_strength for t in transfers) / len(transfers), 2)
        results.append(PlayerInfo(
            name=name,
            transfer_count=len(transfers),
            teams=sorted(teams),
            avg_rumor_strength=avg_strength,
        ))
    return sorted(results, key=lambda p: p.transfer_count, reverse=True)


def get_teams(search: Optional[str] = None) -> list[TeamInfo]:
    all_transfers = store.get_all()
    team_map: dict[str, dict] = {}
    for t in all_transfers:
        for team_name, direction in [(t.from_team, "out"), (t.to_team, "in")]:
            if team_name not in team_map:
                team_map[team_name] = {"incoming": 0, "outgoing": 0, "strengths": [], "targets": []}
            entry = team_map[team_name]
            entry["strengths"].append(t.rumor_strength)
            if direction == "out":
                entry["outgoing"] += 1
                entry["targets"].append(t.to_team)
            else:
                entry["incoming"] += 1
    results = []
    for name, data in team_map.items():
        if search and search.lower() not in name.lower():
            continue
        avg_strength = round(sum(data["strengths"]) / len(data["strengths"]), 2)
        results.append(TeamInfo(
            name=name,
            incoming=data["incoming"],
            outgoing=data["outgoing"],
            avg_rumor_strength=avg_strength,
            top_targets=list(dict.fromkeys(data["targets"]))[:5],
        ))
    return sorted(results, key=lambda t: t.incoming + t.outgoing, reverse=True)
