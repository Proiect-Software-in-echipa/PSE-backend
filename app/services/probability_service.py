from typing import Optional


# Tabele de multiplicatori
SOURCE_MULTIPLIERS = {1: 0.65, 2: 0.80, 3: 0.90, 4: 0.95}
SOURCE_MULTIPLIER_DEFAULT = 1.0  # 5+ surse

CONFIDENCE_THRESHOLDS = [
    (1.0,  "Confirmat"),
    (0.85, "Foarte probabil"),
    (0.65, "Probabil"),
    (0.45, "Posibil"),
    (0.25, "Incert"),
    (0.0,  "Improbabil"),
]


def count_sources(sources_str: str) -> int:
    """Numără sursele dintr-un string separat prin virgulă."""
    if not sources_str or not sources_str.strip():
        return 1
    return len([s.strip() for s in sources_str.split(",") if s.strip()])


def get_source_multiplier(source_count: int) -> float:
    return SOURCE_MULTIPLIERS.get(source_count, SOURCE_MULTIPLIER_DEFAULT)


def calculate_probability(
    rumor_strength: float,
    source_count: int,
    from_team: Optional[str] = None,
    to_team: Optional[str] = None,
    status: Optional[str] = None,
) -> tuple[float, dict]:
    """
    Calculează probabilitatea unui transfer.

    Formula:
      base_score     = rumor_strength / 10
      source_mult    = f(source_count)  → [0.65 .. 1.0]
      raw_prob       = base_score * source_mult
      final_prob     = clamp(raw_prob, 0.02, 0.97)

    Returnează (probability, breakdown).
    """
    is_confirmed = bool(status and status.strip().lower() == "confirmed")

    base_score = rumor_strength / 10.0
    source_mult = get_source_multiplier(source_count)
    raw_prob = base_score * source_mult

    # Penalizare ușoară dacă echipele sunt identice (date greșite)
    same_team_penalty = 0.0
    if from_team and to_team and from_team.lower() == to_team.lower():
        same_team_penalty = 0.30

    adjusted = max(0.0, raw_prob - same_team_penalty)

    if is_confirmed:
        final_prob = 1.0
    else:
        final_prob = round(min(0.97, max(0.02, adjusted)), 4)

    breakdown = {
        "base_score": round(base_score, 4),
        "source_multiplier": source_mult,
        "source_count": source_count,
        "raw_probability": round(raw_prob, 4),
        "same_team_penalty": same_team_penalty,
        "status": status or "Rumor",
        "confirmed_override": is_confirmed,
        "final_probability": final_prob,
    }

    return final_prob, breakdown


def get_confidence_label(probability: float) -> str:
    for threshold, label in CONFIDENCE_THRESHOLDS:
        if probability >= threshold:
            return label
    return "Necunoscut"
