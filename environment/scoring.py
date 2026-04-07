OPEN_SCORE_EPSILON = 1e-4


def normalize_open_score(score: float, *, decimals: int = 4) -> float:
    """Clamp scores into the strict open interval (0, 1)."""
    bounded = max(OPEN_SCORE_EPSILON, min(1.0 - OPEN_SCORE_EPSILON, float(score)))
    return round(bounded, decimals)