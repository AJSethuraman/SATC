"""Small display formatters shared by signals, reports, and UI."""


def pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def money(value: float | None) -> str:
    """Compact USD, e.g. $394.3B / -$1.2M."""
    if value is None:
        return "n/a"
    sign = "-" if value < 0 else ""
    v = abs(value)
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= threshold:
            return f"{sign}${v / threshold:.1f}{suffix}"
    return f"{sign}${v:.0f}"


def ratio(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def shares(value: float | None) -> str:
    if value is None:
        return "n/a"
    v = abs(value)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= threshold:
            return f"{value / threshold:.2f}{suffix}"
    return f"{value:.0f}"


def per_share(value: float | None, digits: int = 2) -> str:
    """Per-share dollars, e.g. $2.35/sh. Rounded — never implies false precision."""
    if value is None:
        return "n/a"
    return f"${value:.{digits}f}/sh"


def multiple(value: float | None, digits: int = 1) -> str:
    """Valuation multiple, e.g. 12.4x. None (undefined) renders as n/m."""
    if value is None:
        return "n/m"
    return f"{value:.{digits}f}x"


def arrow_series(values: list[float], formatter=lambda v: f"{v:.2f}") -> str:
    """Chronological 'a → b → c' rendering of the last few values."""
    return " → ".join(formatter(v) for v in values)
