from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

BRISBANE = ZoneInfo("Australia/Brisbane")

# Queensland / Brisbane public holidays 2025–2026
HOLIDAYS = {
    date(2025, 1, 1),
    date(2025, 1, 27),
    date(2025, 4, 18),
    date(2025, 4, 19),
    date(2025, 4, 21),
    date(2025, 4, 25),
    date(2025, 5, 5),
    date(2025, 8, 13),
    date(2025, 10, 6),
    date(2025, 12, 25),
    date(2025, 12, 26),
    date(2026, 1, 1),
    date(2026, 1, 26),
    date(2026, 4, 3),
    date(2026, 4, 4),
    date(2026, 4, 6),
    date(2026, 4, 25),
    date(2026, 4, 27),
    date(2026, 5, 4),
    date(2026, 8, 12),
    date(2026, 10, 5),
    date(2026, 12, 25),
    date(2026, 12, 26),
    date(2026, 12, 28),
}


def is_qld_holiday(d: date) -> bool:
    return d in HOLIDAYS


def day_class(d: date) -> str:
    if is_qld_holiday(d):
        return "holiday"
    return "weekend" if d.weekday() >= 5 else "weekday"


def season(d: date) -> str:
    m = d.month
    if m in (12, 1, 2):
        return "summer"
    if m in (3, 4, 5):
        return "autumn"
    if m in (6, 7, 8):
        return "winter"
    return "spring"


def brisbane_clock() -> tuple[str, str, int, str, str, bool]:
    now = datetime.now(BRISBANE)
    # Forecast the current hour. ponytail: still returned/serialised as `next_hour`
    # to avoid an API field rename; rename across py/rs/web if the name confuses.
    target = now.date()
    return (
        now.strftime("%Y-%m-%d %H:%M AEST"),
        target.isoformat(),
        now.hour,
        day_class(target),
        season(target),
        is_qld_holiday(target),
    )


def chance_free(occupancy_pred: float) -> float:
    return max(0.0, min(1.0, (5.0 - occupancy_pred) / 5.0))


def chance_label(chance: float | None, *, parkable: bool = True, status_label: str | None = None) -> str:
    if not parkable and status_label:
        return status_label
    if chance is None:
        return "Unknown"
    if chance >= 0.6:
        return "Likely"
    if chance >= 0.35:
        return "Mixed"
    return "Unlikely"
