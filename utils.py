"""
Utility functions — time calculations, business days, formatting.
"""

from datetime import date, time, datetime, timedelta
from typing import Any

from database import (
    get_setting,
    get_time_entries,
    get_allocations_for_entry,
    is_holiday,
)


def parse_time(value: str | None) -> time | None:
    """Parse HH:MM string to time, or return None."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        return None


def time_to_str(t: time | None) -> str:
    """Format time as HH:MM, or empty string."""
    if t is None:
        return ""
    return t.strftime("%H:%M")


def calculate_worked_hours(
    start_time: time | None,
    lunch_start: time | None,
    lunch_end: time | None,
    end_time: time | None,
) -> float:
    """Return worked hours as a float.
    Formula: (end - start) - (lunch_end - lunch_start).
    Returns 0 if any required field is missing.
    """
    if not all([start_time, lunch_start, lunch_end, end_time]):
        return 0.0

    today = date.today()
    start_dt = datetime.combine(today, start_time)
    lunch_start_dt = datetime.combine(today, lunch_start)
    lunch_end_dt = datetime.combine(today, lunch_end)
    end_dt = datetime.combine(today, end_time)

    # Handle end_time past midnight (e.g., 23:00 → 01:00)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    total_minutes = (end_dt - start_dt).total_seconds() / 60
    lunch_minutes = (lunch_end_dt - lunch_start_dt).total_seconds() / 60

    if lunch_minutes < 0:
        lunch_minutes = 0

    worked_minutes = total_minutes - lunch_minutes
    return round(max(worked_minutes, 0) / 60, 2)


def format_hours(hours: float) -> str:
    """Format float hours as H:MM."""
    if hours <= 0:
        return "0:00"
    h = int(hours)
    m = int(round((hours - h) * 60))
    return f"{h}:{m:02d}"


def float_to_hours_minutes(hours: float) -> tuple[int, int]:
    """Return (hours, minutes) from a float."""
    h = int(hours)
    m = int(round((hours - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return h, m


def is_business_day(check_date: date) -> bool:
    """Return True if the date is a business day (not weekend, not holiday).
    Respects the ignore_weekends setting.
    """
    ignore_weekends = get_setting("ignore_weekends", "1") == "1"
    if ignore_weekends and check_date.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if is_holiday(check_date):
        return False
    return True


def count_business_days(year: int, month: int) -> int:
    """Count business days in a given month."""
    count = 0
    d = date(year, month, 1)
    # Go to the next month
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    while d < end:
        if is_business_day(d):
            count += 1
        d += timedelta(days=1)
    return count


def count_business_days_range(start_date: date, end_date: date) -> int:
    """Count business days between two dates (inclusive)."""
    count = 0
    d = start_date
    while d <= end_date:
        if is_business_day(d):
            count += 1
        d += timedelta(days=1)
    return count


def get_expected_hours_for_period(start_date: date, end_date: date) -> float:
    """Calculate expected hours for a date range based on daily_hours setting."""
    daily = float(get_setting("daily_hours", "8"))
    days = count_business_days_range(start_date, end_date)
    return daily * days


def calculate_hours_balance(
    start_date: date, end_date: date
) -> float:
    """Calculate the hours balance for a period.
    balance = total worked - expected hours (considering only business days).
    """
    expected = get_expected_hours_for_period(start_date, end_date)
    entries = get_time_entries(start_date, end_date, order_desc=False)

    total_worked = 0.0
    for entry in entries:
        worked = calculate_worked_hours(
            parse_time(entry["start_time"]),
            parse_time(entry["lunch_start"]),
            parse_time(entry["lunch_end"]),
            parse_time(entry["end_time"]),
        )
        total_worked += worked

    return round(total_worked - expected, 2)


def get_daily_hours_with_projects(entry: dict) -> dict[str, Any]:
    """Enrich a time_entry dict with calculated hours and project info."""
    worked = calculate_worked_hours(
        parse_time(entry["start_time"]),
        parse_time(entry["lunch_start"]),
        parse_time(entry["lunch_end"]),
        parse_time(entry["end_time"]),
    )
    allocations = get_allocations_for_entry(entry["id"])
    project_names = ", ".join(a["project_name"] for a in allocations) if allocations else "—"
    company_names_list = [a.get("company_name") for a in allocations if a.get("company_name")]
    # Preserve order while removing duplicates
    seen: set[str] = set()
    unique_companies = [c for c in company_names_list if not (c in seen or seen.add(c))]
    company_names = ", ".join(unique_companies) if unique_companies else "—"
    allocated_hours = sum(a["hours"] for a in allocations)

    return {
        **entry,
        "worked_hours": worked,
        "worked_hours_str": format_hours(worked),
        "project_names": project_names,
        "company_names": company_names,
        "allocated_hours": allocated_hours,
        "allocations": allocations,
    }


def get_weekday_name(d: date) -> str:
    """Return weekday abbreviation in Portuguese."""
    names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    return names[d.weekday()]


def date_range_this_week(today: date | None = None) -> tuple[date, date]:
    """Return (monday, sunday) for the current week."""
    if today is None:
        today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def date_range_this_month(today: date | None = None) -> tuple[date, date]:
    """Return (first_day, last_day) for the current month."""
    if today is None:
        today = date.today()
    first = today.replace(day=1)
    if today.month == 12:
        last = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first, last


def has_entry_today() -> tuple[bool, bool]:
    """Check if there's an entry for today.
    Returns (has_entry, has_exit).
    """
    today = date.today()
    entries = get_time_entries(today, today, order_desc=False)
    if not entries:
        return False, False
    latest = entries[-1]
    has_exit = latest.get("end_time") is not None
    return True, has_exit
