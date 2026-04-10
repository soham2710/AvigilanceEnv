OPEN_SCORE_EPSILON = 1e-4


def normalize_open_score(score: float, *, decimals: int = 4) -> float:
    """Clamp scores into the strict open interval (0, 1)."""
    bounded = max(OPEN_SCORE_EPSILON, min(1.0 - OPEN_SCORE_EPSILON, float(score)))
    return round(bounded, decimals)


def format_open_score(score: float, *, decimals: int) -> str:
    """Format scores so rounding for display cannot produce 0 or 1."""
    display_epsilon = 10 ** (-decimals)
    bounded = max(display_epsilon, min(1.0 - display_epsilon, float(score)))
    return f"{bounded:.{decimals}f}"


def format_open_score_compact(score: float, *, decimals: int = 4) -> str:
    """Format scores inside (0, 1) without padded trailing zeroes."""
    bounded = normalize_open_score(score, decimals=decimals)
    return f"{bounded:.{decimals}f}".rstrip("0").rstrip(".")