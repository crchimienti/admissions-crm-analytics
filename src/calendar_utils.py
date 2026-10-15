"""Business-day and working-hour helpers (v1: Monday-Friday, no holidays).

Ayudas de calendario: días hábiles lunes-viernes, sin festivos en v1.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

OPEN_HOUR = 9
CLOSE_HOUR = 19


def is_business_day(d: date) -> bool:
    return d.weekday() < 5


def add_business_days(d: date, n: int) -> date:
    """Return the n-th business day after d (n >= 0). BD0 = d itself."""
    if n < 0:
        raise ValueError("n must be >= 0")
    cur = d
    while n > 0:
        cur += timedelta(days=1)
        if is_business_day(cur):
            n -= 1
    return cur


def next_business_day(d: date) -> date:
    """Same day if it is a business day, otherwise the next business day."""
    cur = d
    while not is_business_day(cur):
        cur += timedelta(days=1)
    return cur


def business_days_between(d0: date, d1: date) -> int:
    """Number of business days from d0 to d1 (d1 >= d0), excluding d0."""
    n, cur = 0, d0
    while cur < d1:
        cur += timedelta(days=1)
        if is_business_day(cur):
            n += 1
    return n


def _at(d: date, hour: float) -> datetime:
    return datetime.combine(d, time(0)) + timedelta(hours=hour)


def next_working_time(ts: datetime) -> datetime:
    """ts itself if inside working hours, otherwise the next opening."""
    d = ts.date()
    if is_business_day(d):
        if ts < _at(d, OPEN_HOUR):
            return _at(d, OPEN_HOUR)
        if ts < _at(d, CLOSE_HOUR):
            return ts
    return _at(add_business_days(d, 1) if is_business_day(d) else next_business_day(d), OPEN_HOUR)


def add_business_hours(ts: datetime, hours: float) -> datetime:
    """Advance ts by `hours` of working time (Mon-Fri 09-19)."""
    t = next_working_time(ts)
    remaining = hours
    while True:
        close = _at(t.date(), CLOSE_HOUR)
        avail = (close - t).total_seconds() / 3600
        if remaining <= avail:
            return t + timedelta(hours=remaining)
        remaining -= avail
        t = _at(add_business_days(t.date(), 1), OPEN_HOUR)


def at_hour(d: date, hour: float) -> datetime:
    return _at(d, hour)
