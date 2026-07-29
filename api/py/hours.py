"""Parse BCC meter OPERATIONAL_* and RESTRICTIONS for parkability at a given Brisbane time."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time

from .timectx import is_qld_holiday

DAY_ALIASES = {
    "MON": 0,
    "M": 0,
    "TUE": 1,
    "TU": 1,
    "WED": 2,
    "W": 2,
    "THU": 3,
    "TH": 3,
    "FRI": 4,
    "F": 4,
    "SAT": 5,
    "SA": 5,
    "SUN": 6,
    "SU": 6,
}


@dataclass(frozen=True)
class ParkStatus:
    parkable: bool
    status: str  # operating | closed | restricted
    reason: str
    label: str


def _parse_clock(token: str) -> time | None:
    token = token.strip().upper().replace(" ", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(AM|PM)$", token)
    if not m:
        # bare hour like 7-10PM handled elsewhere
        m = re.match(r"^(\d{1,2})(AM|PM)$", token)
        if not m:
            return None
        hour = int(m.group(1))
        ampm = m.group(2)
        minute = 0
    else:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = m.group(3)
    if hour == 12:
        hour = 0
    if ampm == "PM":
        hour += 12
    if hour > 23:
        return None
    return time(hour, minute)


def _hour_in_range(hour: int, start: time, end: time) -> bool:
    sh, eh = start.hour, end.hour
    if eh == 0 and end.minute == 0 and sh > 0:
        eh = 24
    if sh <= eh:
        return sh <= hour < eh
    return hour >= sh or hour < eh


def _days_from_token(token: str) -> set[int] | None:
    token = token.upper().replace(" ", "")
    if not token:
        return None
    if token in ("7DAYS", "DAILY", "EVERYDAY"):
        return set(range(7))
    if "-" in token and "&" not in token:
        parts = token.split("-")
        if len(parts) == 2 and parts[0] in DAY_ALIASES and parts[1] in DAY_ALIASES:
            a, b = DAY_ALIASES[parts[0]], DAY_ALIASES[parts[1]]
            if a <= b:
                return set(range(a, b + 1))
            return set(range(a, 7)) | set(range(0, b + 1))
    if "," in token:
        out: set[int] = set()
        for p in token.split(","):
            d = _days_from_token(p)
            if d:
                out |= d
        return out or None
    if token in DAY_ALIASES:
        return {DAY_ALIASES[token]}
    return None


def _effective_weekday(d: date) -> int:
    """BCC paid parking on QLD public holidays generally follows Sunday rules."""
    if is_qld_holiday(d):
        return 6  # Sunday
    return d.weekday()


def _extract_windows(operational_day: str, operational_time: str) -> list[tuple[set[int], time, time]]:
    """
    Return list of (days, start, end) windows.
    Falls back to OPERATIONAL_DAY + a single simple range when time string is plain.
    """
    day_default = _days_from_token((operational_day or "").replace(" ", "")) or set(range(5))
    raw = (operational_time or "").upper()
    raw = raw.replace("&", ",").replace("–", "-").replace("—", "-")

    windows: list[tuple[set[int], time, time]] = []

    # Patterns like 7AM-7PM(MON-FRI) or 7PM-10PM(MON-FRI)
    for m in re.finditer(
        r"(\d{1,2}(?::\d{2})?AM|\d{1,2}(?::\d{2})?PM)\s*-\s*(\d{1,2}(?::\d{2})?AM|\d{1,2}(?::\d{2})?PM)"
        r"(?:\s*\(([A-Z0-9,\-]+)\))?",
        raw,
    ):
        start = _parse_clock(m.group(1))
        end = _parse_clock(m.group(2))
        if not start or not end:
            continue
        days = _days_from_token(m.group(3)) if m.group(3) else None
        # Trailing day words after range without parens: "7PM-10PM MON-FRI"
        if days is None:
            after = raw[m.end() : m.end() + 24]
            dm = re.match(r"[\s,]*([A-Z]{3}-[A-Z]{3}|MON-FRI|SAT-SUN|7\s*DAYS)", after)
            if dm:
                days = _days_from_token(dm.group(1).replace(" ", ""))
        windows.append((days or day_default, start, end))

    # Also catch "7AM-7PM MON-FRI" style where days follow without paren (already partially handled)
    if not windows:
        m = re.search(
            r"(\d{1,2}(?::\d{2})?AM|\d{1,2}(?::\d{2})?PM)\s*-\s*(\d{1,2}(?::\d{2})?AM|\d{1,2}(?::\d{2})?PM)",
            raw,
        )
        if m:
            start = _parse_clock(m.group(1))
            end = _parse_clock(m.group(2))
            if start and end:
                windows.append((day_default, start, end))

    return windows


def is_within_operating_hours(
    operational_day: str,
    operational_time: str,
    when: datetime,
) -> bool:
    windows = _extract_windows(operational_day, operational_time)
    if not windows:
        # Unknown schedule — don't block the user
        return True
    wd = _effective_weekday(when.date())
    hour = when.hour
    for days, start, end in windows:
        if wd not in days:
            continue
        sh, eh = start.hour, end.hour
        if eh == 0 and end.minute == 0:
            eh = 24
        if sh <= hour < eh:
            return True
        # overnight window
        if sh > eh and (hour >= sh or hour < eh):
            return True
    return False


def active_restriction(restrictions: str, when: datetime) -> str | None:
    """
    Return a short reason if clearway / no stopping / bus / loading blocks parking now.
    Motorcycle-only zones always block typical car parking.
    """
    text = (restrictions or "").strip().upper()
    if not text or text == "NONE":
        return None

    if "M/C PARKING ONLY" in text or "MOTORCYCLE" in text:
        return "Motorcycle parking only"

    wd = _effective_weekday(when.date())
    hour = when.hour

    # Split on common separators between restriction clauses
    clauses = re.split(r"(?=\b(?:CLEARWAY|NO STOPPING|BUS ZONE|LOADING ZONE)\b)", text)
    for clause in clauses:
        clause = clause.strip(" ,;")
        if not clause:
            continue
        kind = None
        if clause.startswith("CLEARWAY"):
            kind = "Clearway (towaway)"
        elif clause.startswith("NO STOPPING"):
            kind = "No stopping"
        elif clause.startswith("BUS ZONE"):
            kind = "Bus zone"
        elif clause.startswith("LOADING ZONE"):
            kind = "Loading zone only"
        else:
            continue

        # Days: default MON-FRI if mentioned, else weekdays for these restriction types
        days = set(range(5))
        dm = re.search(r"(MON-FRI|SAT-SUN|MON-SAT|7\s*DAYS|[A-Z]{3}-[A-Z]{3})", clause)
        if dm:
            parsed = _days_from_token(dm.group(1).replace(" ", ""))
            if parsed:
                days = parsed
        if wd not in days:
            continue

        # Time ranges in clause: 7AM-9AM,4PM-7PM
        ranges = re.findall(
            r"(\d{1,2}(?::\d{2})?AM|\d{1,2}(?::\d{2})?PM)\s*-\s*(\d{1,2}(?::\d{2})?AM|\d{1,2}(?::\d{2})?PM)",
            clause,
        )
        if not ranges:
            # All-day style restriction on those days
            return kind
        for a, b in ranges:
            start, end = _parse_clock(a), _parse_clock(b)
            if not start or not end:
                continue
            eh = 24 if end.hour == 0 and end.minute == 0 else end.hour
            if start.hour <= hour < eh:
                return kind
    return None


def target_datetime(date_str: str, hour: int) -> datetime:
    from zoneinfo import ZoneInfo

    d = date.fromisoformat(date_str)
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=ZoneInfo("Australia/Brisbane"))


def evaluate_parkability(
    *,
    operational_day: str,
    operational_time: str,
    restrictions: str,
    date_str: str,
    hour: int,
) -> ParkStatus:
    when = target_datetime(date_str, hour)

    blocked = active_restriction(restrictions, when)
    if blocked:
        return ParkStatus(
            parkable=False,
            status="restricted",
            reason=blocked,
            label="No parking",
        )

    if not is_within_operating_hours(operational_day, operational_time, when):
        return ParkStatus(
            parkable=False,
            status="closed",
            reason="Outside paid parking hours",
            label="Closed",
        )

    return ParkStatus(
        parkable=True,
        status="operating",
        reason="Within paid parking hours",
        label="Open",
    )
