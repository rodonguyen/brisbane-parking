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
    status: str  # operating | free | restricted
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
    token = token.upper().replace(" ", "").replace("&", "")
    if not token:
        return None
    # Compact BCC day spans (M-F must not become {Mon, Fri} only)
    if token in ("7DAYS", "DAILY", "EVERYDAY"):
        return set(range(7))
    if token in ("MF", "M-F", "MFRI", "M-FRI", "MONFRI", "MON-FRI"):
        return set(range(5))
    if token in ("SS", "S-S", "SATSUN", "SAT-SUN"):
        return {5, 6}
    if token in ("MONSAT", "MON-SAT"):
        return set(range(6))
    if "-" in token:
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


def _normalize_restrictions(text: str) -> str:
    """Expand common BCC abbreviations before clause parsing."""
    t = text.upper().replace("–", "-").replace("—", "-")
    t = t.replace("T'AWAY", "TOWAWAY")
    t = t.replace("C/WAY", "CLEARWAY")
    t = re.sub(r"\bC/W\b", "CLEARWAY", t)
    t = re.sub(r"\bN/S\b", "NO STOPPING", t)
    t = re.sub(r"\bLOAD ZONE\b", "LOADING ZONE", t)
    t = re.sub(r"\bLZ\b", "LOADING ZONE", t)
    t = re.sub(r"\bBZ\b", "BUS ZONE", t)
    t = re.sub(r"\bM-FRI\b", "MON-FRI", t)
    t = re.sub(r"\bM-F\b", "MON-FRI", t)
    t = re.sub(r"\bS&S\b", "SAT-SUN", t)
    t = re.sub(r"\bS-S\b", "SAT-SUN", t)
    t = re.sub(r"\bAOT\b", "ALL OTHER TIMES", t)
    # "7-9 AM" / "4-7 PM" → "7-9AM" / "4-7PM"
    t = re.sub(r"(\d)\s+(AM|PM)\b", r"\1\2", t)
    return t


_KIND_LABELS = {
    "CLEARWAY": "Clearway (towaway)",
    "NO STOPPING": "No stopping",
    "BUS ZONE": "Bus zone",
    "LOADING ZONE": "Loading zone only",
    "TAXI ZONE": "Taxi zone",
}

_KIND_ALT = "|".join(re.escape(k) for k in _KIND_LABELS)
_KIND_RE = re.compile(rf"(?P<kind>{_KIND_ALT})\b")

# 7AM-9AM | 7-9AM | 2:30-7PM | 7-9 AM (spaces normalized upstream)
_TIME_RANGE_RE = re.compile(
    r"(?P<a>\d{1,2}(?::\d{2})?)\s*(?P<a_ap>AM|PM)?"
    r"\s*-\s*"
    r"(?P<b>\d{1,2}(?::\d{2})?)\s*(?P<b_ap>AM|PM)"
)

_DAY_SPAN_RE = re.compile(
    r"(MON-FRI|SAT-SUN|MON-SAT|7\s*DAYS|M-F|M-FRI|S-S|[A-Z]{3}-[A-Z]{3})"
)


def _parse_time_ranges(fragment: str) -> list[tuple[time, time]]:
    out: list[tuple[time, time]] = []
    for m in _TIME_RANGE_RE.finditer(fragment):
        b_ap = m.group("b_ap")
        a_ap = m.group("a_ap") or b_ap
        start = _parse_clock(f"{m.group('a')}{a_ap}")
        end = _parse_clock(f"{m.group('b')}{b_ap}")
        if start and end:
            out.append((start, end))
    return out


def _parse_days(fragment: str, default: set[int]) -> set[int]:
    dm = _DAY_SPAN_RE.search(fragment)
    if not dm:
        return default
    parsed = _days_from_token(dm.group(1).replace(" ", ""))
    return parsed if parsed else default


def _hour_matches_range(hour: int, start: time, end: time) -> bool:
    sh, eh = start.hour, end.hour
    if eh == 0 and end.minute == 0 and sh > 0:
        eh = 24
    if sh <= eh:
        return sh <= hour < eh
    return hour >= sh or hour < eh


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
        if _hour_matches_range(hour, start, end):
            return True
    return False


def active_restriction(restrictions: str, when: datetime) -> str | None:
    """
    Return a short reason if clearway / no stopping / bus / loading blocks parking now.
    Motorcycle-only zones always block typical car parking.
    """
    raw = (restrictions or "").strip()
    if not raw or raw.upper() in ("NONE", "NIL"):
        return None

    text = _normalize_restrictions(raw)
    if "M/C PARKING ONLY" in text or "MOTORCYCLE" in text:
        return "Motorcycle parking only"

    wd = _effective_weekday(when.date())
    hour = when.hour
    default_days = set(range(5))

    # Global day span if present once for the whole string
    global_days = _parse_days(text, default_days)

    # Split into kind + trailing body (times/days until next kind)
    parts = re.split(rf"(?=(?:{_KIND_ALT})\b)", text)
    clauses: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip(" ,;&")
        if not part:
            continue
        m = _KIND_RE.match(part)
        if not m:
            # Times-before-kind: "7AM-9AM & 4PM-7PM NO STOPPING"
            km = re.search(rf"({_KIND_ALT})\b", part)
            if not km:
                continue
            kind = km.group(1)
            body = (part[: km.start()] + " " + part[km.end() :]).strip(" ,;&")
            clauses.append((kind, body))
            continue
        kind = m.group("kind")
        body = part[m.end() :].strip(" ,;&")
        clauses.append((kind, body))

    if not clauses:
        return None

    # Propagate time ranges across "CLEARWAY & LOADING ZONE 7AM-7PM" style joins:
    # earlier kinds with empty bodies inherit ranges from the next body that has them.
    parsed: list[tuple[str, list[tuple[time, time]], set[int], bool]] = []
    for kind, body in clauses:
        ranges = _parse_time_ranges(body)
        days = _parse_days(body, global_days)
        aot = "ALL OTHER TIMES" in body
        parsed.append((kind, ranges, days, aot))

    for i, (kind, ranges, days, aot) in enumerate(parsed):
        if ranges or aot:
            continue
        for j in range(i + 1, len(parsed)):
            if parsed[j][1]:
                parsed[i] = (kind, parsed[j][1], days or parsed[j][2], aot)
                break

    # Severity order when multiple kinds share a window
    severity = {
        "CLEARWAY": 0,
        "NO STOPPING": 1,
        "BUS ZONE": 2,
        "LOADING ZONE": 3,
        "TAXI ZONE": 4,
    }
    timed_hits: list[tuple[int, str]] = []
    aot_hits: list[tuple[int, str]] = []

    for kind, ranges, days, aot in parsed:
        if wd not in days:
            continue
        label = _KIND_LABELS[kind]
        if ranges:
            for start, end in ranges:
                if _hour_matches_range(hour, start, end):
                    timed_hits.append((severity[kind], label))
                    break
        elif aot:
            aot_hits.append((severity[kind], label))
        else:
            # No explicit times → treat as in force on those days
            timed_hits.append((severity[kind], label))

    if timed_hits:
        timed_hits.sort(key=lambda x: x[0])
        return timed_hits[0][1]

    # AOT only applies when no timed restriction matched this hour
    if aot_hits:
        # Re-check: AOT means "when not in another timed window on this string"
        any_timed = any(ranges for _k, ranges, _d, _a in parsed if ranges)
        if any_timed:
            aot_hits.sort(key=lambda x: x[0])
            return aot_hits[0][1]
        aot_hits.sort(key=lambda x: x[0])
        return aot_hits[0][1]

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
        # Off-meter: usually free street parking unless a restriction matched above.
        return ParkStatus(
            parkable=True,
            status="free",
            reason="Outside paid parking hours",
            label="Free",
        )

    return ParkStatus(
        parkable=True,
        status="operating",
        reason="Within paid parking hours",
        label="Open",
    )
