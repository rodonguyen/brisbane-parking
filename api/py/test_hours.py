"""Parkability / restriction parsing checks."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from py.hours import active_restriction, evaluate_parkability

BNE = ZoneInfo("Australia/Brisbane")


def _dt(hour: int, day: int = 29) -> datetime:
    # 2026-07-29 is Wednesday
    return datetime(2026, 7, day, hour, 0, tzinfo=BNE)


def test_ann_st_cway_lz_at_5pm_is_restricted():
    restr = "C/WAY & LZ 7AM-7PM MON-FRI TOWAWAY"
    assert active_restriction(restr, _dt(17)) == "Clearway (towaway)"
    st = evaluate_parkability(
        operational_day="7 DAYS",
        operational_time="7PM-10PM MON-FRI, 7AM-7PM SAT-SUN",
        restrictions=restr,
        date_str="2026-07-29",
        hour=17,
    )
    assert st.status == "restricted"
    assert st.parkable is False


def test_ann_st_after_7pm_not_restricted_by_cway():
    restr = "C/WAY & LZ 7AM-7PM MON-FRI TOWAWAY"
    assert active_restriction(restr, _dt(20)) is None


def test_full_clearway_still_works():
    restr = "CLEARWAY 7AM-9AM,4PM-7PM MON-FRI TOWAWAY"
    assert active_restriction(restr, _dt(17)) == "Clearway (towaway)"
    assert active_restriction(restr, _dt(12)) is None


def test_abbrev_cw_and_compact_times():
    restr = "C/W 7-11AM,2-7PM MON-SAT TOWAWAY"
    assert active_restriction(restr, _dt(15)) == "Clearway (towaway)"
    assert active_restriction(restr, datetime(2026, 7, 26, 15, 0, tzinfo=BNE)) is None  # Sunday


def test_ns_and_lz_aot():
    restr = "N/S 7-9 AM, BUS ZONE 4-7 PM MON-FRI, LZ AOT"
    assert active_restriction(restr, _dt(8)) == "No stopping"
    assert active_restriction(restr, _dt(17)) == "Bus zone"
    assert active_restriction(restr, _dt(12)) == "Loading zone only"


def test_shared_cway_lz_windows():
    restr = "C/WAY 7AM-9AM, 4PM-7PM & LZ 9AM-4PM MON-FRI"
    assert active_restriction(restr, _dt(8)) == "Clearway (towaway)"
    assert active_restriction(restr, _dt(12)) == "Loading zone only"
    assert active_restriction(restr, _dt(17)) == "Clearway (towaway)"


def test_outside_paid_hours_still_free_without_restriction():
    st = evaluate_parkability(
        operational_day="MON-FRI",
        operational_time="7AM-7PM",
        restrictions="NONE",
        date_str="2026-07-29",
        hour=20,
    )
    assert st.status == "free"
    assert st.parkable is True


if __name__ == "__main__":
    test_ann_st_cway_lz_at_5pm_is_restricted()
    test_ann_st_after_7pm_not_restricted_by_cway()
    test_full_clearway_still_works()
    test_abbrev_cw_and_compact_times()
    test_ns_and_lz_aot()
    test_shared_cway_lz_windows()
    test_outside_paid_hours_still_free_without_restriction()
    print("ok")
