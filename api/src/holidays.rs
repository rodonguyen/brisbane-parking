use chrono::{Datelike, NaiveDate};

/// Queensland (Brisbane) public holidays for 2025–2026.
pub fn is_qld_holiday(date: NaiveDate) -> bool {
    HOLIDAYS.iter().any(|&d| d == date)
}

pub fn day_class(date: NaiveDate) -> &'static str {
    if is_qld_holiday(date) {
        "holiday"
    } else {
        match date.weekday().number_from_monday() {
            6 | 7 => "weekend",
            _ => "weekday",
        }
    }
}

pub fn season(date: NaiveDate) -> &'static str {
    match date.month() {
        12 | 1 | 2 => "summer",
        3 | 4 | 5 => "autumn",
        6 | 7 | 8 => "winter",
        _ => "spring",
    }
}

const HOLIDAYS: &[NaiveDate] = &[
    // 2025
    d(2025, 1, 1),
    d(2025, 1, 27),
    d(2025, 4, 18),
    d(2025, 4, 19),
    d(2025, 4, 21),
    d(2025, 4, 25),
    d(2025, 5, 5),
    d(2025, 8, 13),
    d(2025, 10, 6),
    d(2025, 12, 25),
    d(2025, 12, 26),
    // 2026
    d(2026, 1, 1),
    d(2026, 1, 26),
    d(2026, 4, 3),
    d(2026, 4, 4),
    d(2026, 4, 6),
    d(2026, 4, 25),
    d(2026, 4, 27),
    d(2026, 5, 4),
    d(2026, 8, 12),
    d(2026, 10, 5),
    d(2026, 12, 25),
    d(2026, 12, 26),
    d(2026, 12, 28),
];

const fn d(y: i32, m: u32, day: u32) -> NaiveDate {
    match NaiveDate::from_ymd_opt(y, m, day) {
        Some(date) => date,
        None => panic!("invalid holiday date"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn australia_day_2026_is_holiday() {
        assert!(is_qld_holiday(d(2026, 1, 26)));
        assert_eq!(day_class(d(2026, 1, 26)), "holiday");
    }

    #[test]
    fn winter_july() {
        assert_eq!(season(d(2026, 7, 29)), "winter");
    }
}
