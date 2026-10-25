"""Car park shaping: readable rate rows, hours, and which links to show."""

from __future__ import annotations

import unittest

from py.carparks import hours_lines, rate_groups, shape, simplify_hours


def _rate(kind, label, price=None, online=None, **kw):
    return {"kind": kind, "label": label, "price_aud": price, "online_price_aud": online,
            "days": kw.get("days"), "entry_window": kw.get("entry"), "exit_window": kw.get("exit"),
            "duration_hours_from": kw.get("f"), "duration_hours_to": kw.get("t"), "conditions": None}


class RateGroupsTest(unittest.TestCase):
    def test_casual_bands_read_as_durations(self):
        g = rate_groups([
            _rate("hourly", "Casual Parking - 0 - 30 Min", 0, f=0, t=0.5),
            _rate("hourly", "Casual Parking - 0.5 - 1 Hour", 18, 14, f=0.5, t=1),
            _rate("daily_max", "4+ Hours (max daily)", 36, 30, f=4),
        ])
        self.assertEqual(g[0]["title"], "Casual")
        rows = g[0]["rows"]
        self.assertEqual((rows[0]["label"], rows[0]["price"]), ("Up to 30 min", "Free"))
        self.assertEqual((rows[1]["label"], rows[1]["price"], rows[1]["online_price"]), ("30 min – 1 hr", "$18", "$14"))
        self.assertEqual(rows[2]["label"], "Max per day")

    def test_heading_repeat_dropped_and_window_kept(self):
        g = rate_groups([_rate("early_bird", "Early Bird Parking - Flat Rate", None, 20,
                               days="Mon-Fri", entry="06:30-09:00", exit="12:00-19:00")])
        row = g[0]["rows"][0]
        self.assertIsNone(row["label"])
        self.assertEqual(row["when"], "Mon-Fri, enter 6:30am – 9am, exit 12pm – 7pm")
        self.assertIsNone(row["price"])
        self.assertEqual(row["online_price"], "$20")

    def test_named_flat_rate_keeps_its_name_and_daily_window_shown(self):
        g = {x["title"]: x["rows"] for x in rate_groups([
            _rate("flat", "Overnight & Hotel Parking (24hr, pre-book)", None, 40, f=0, t=24),
            _rate("daily_max", "Daily flat rate", 52, 41.6, days="Mon-Fri", entry="04:00-16:00", exit="-04:00"),
            _rate("night", "Night Parking - 0- 2 Hours", 0, f=0, t=2),
        ])}
        self.assertEqual(g["Flat rate"][0]["label"], "Overnight & Hotel Parking (24hr, pre-book)")
        self.assertEqual(g["Casual"][0]["when"], "Mon-Fri, enter 4am – 4pm, exit before 4am")
        self.assertEqual(g["Night"][0]["label"], "Up to 2 hrs")

    def test_lost_ticket_and_unpriced_rows_hidden(self):
        g = rate_groups([_rate("other", "Lost Ticket", 55), _rate("night", "Night", None, None)])
        self.assertEqual(g, [])

    def test_same_online_price_not_repeated(self):
        row = rate_groups([_rate("weekend", "Weekend Parking - Flat Rate", 13.5, 13.5, days="Sat-Sun")])[0]["rows"][0]
        self.assertEqual((row["price"], row["online_price"]), ("$13.50", None))


class HoursTest(unittest.TestCase):
    def test_simplify(self):
        self.assertEqual(simplify_hours("24/7"), "Open 24/7")
        self.assertEqual(simplify_hours("Mon-Sun: 24 Hours; Public Holidays: 24 Hours"), "Open 24/7")
        self.assertEqual(simplify_hours("Mon-Sun: 07:00 AM - 08:30 PM; Public Holidays: 07:00 AM - 08:30 PM"),
                         "Daily 7am – 8:30pm")
        self.assertIsNone(simplify_hours(None))

    def test_per_day_hours_grouped_and_short(self):
        h = ("Mon: 05:00 AM - 12:00 AM; Tue: 05:00 AM - 12:00 AM; Wed: 05:00 AM - 12:00 AM; "
             "Thu: 05:00 AM - 12:00 AM; Fri: 05:00 AM - 12:00 AM; Sat: 07:00 AM - 12:00 AM; "
             "Sun: 07:00 AM - 12:00 AM; Public Holidays: Closed")
        self.assertEqual(hours_lines(h), [
            {"days": "Mon–Fri", "time": "5am – 12am"},
            {"days": "Sat–Sun", "time": "7am – 12am"},
            {"days": "Public holidays", "time": "Closed"},
        ])

    def test_24h_clock_and_free_text(self):
        self.assertEqual(hours_lines("Mon-Fri 06:00-22:30; Sat-Sun 09:00-22:00; Monthly subscribers 24 hours"),
                         [{"days": "Mon–Fri", "time": "6am – 10:30pm"}, {"days": "Sat–Sun", "time": "9am – 10pm"}])
        self.assertEqual(hours_lines("6:00am – 6:00pm, Monday – Sunday"), [{"days": "Daily", "time": "6am – 6pm"}])
        self.assertEqual(hours_lines("Monthly Parking Only 24/7 Access"),
                         [{"days": None, "time": "Monthly Parking Only 24/7 Access"}])


class ShapeTest(unittest.TestCase):
    def test_shared_urls_dropped_and_no_coords_skipped(self):
        base = {"name": "A", "operator": "Op", "address": "1 X St, Australia", "hours": None,
                "height_m": None, "rates": []}
        recs = [
            {**base, "id": "a", "lat": -27.4, "lng": 153.0, "url": "https://op.example/a"},
            {**base, "id": "b", "lat": -27.4, "lng": 153.0, "url": "https://council.example/car-parks"},
            {**base, "id": "c", "lat": -27.4, "lng": 153.0, "url": "https://council.example/car-parks"},
            {**base, "id": "d", "lat": None, "lng": None, "url": "https://op.example/d"},
        ]
        out = {c["id"]: c for c in shape(recs)}
        self.assertEqual(set(out), {"a", "b", "c"})
        self.assertEqual(out["a"]["url"], "https://op.example/a")
        self.assertIsNone(out["b"]["url"])
        self.assertEqual(out["a"]["address"], "1 X St")
        self.assertFalse(out["a"]["priced"])


if __name__ == "__main__":
    unittest.main()
