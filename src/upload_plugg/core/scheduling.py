from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ScheduleError(ValueError):
    pass


def calculate_schedule(
    count: int,
    start_date: date,
    enabled_weekdays: list[int],
    default_time: time,
    timezone_name: str = "Europe/Berlin",
    per_day_times: dict[int, time] | None = None,
    now: datetime | None = None,
) -> list[datetime]:
    if count < 1:
        return []
    if not enabled_weekdays:
        raise ScheduleError("Enable at least one schedule day.")
    if any(day not in range(7) for day in enabled_weekdays):
        raise ScheduleError("A weekday value is invalid.")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ScheduleError(f"Unknown timezone: {timezone_name}") from exc
    current = now.astimezone(zone) if now else datetime.now(zone)
    day = start_date
    results: list[datetime] = []
    enabled = set(enabled_weekdays)
    per_day_times = per_day_times or {}
    safety = 0
    while len(results) < count:
        safety += 1
        if safety > count * 14 + 14:
            raise ScheduleError("Could not calculate enough publication slots.")
        if day.weekday() in enabled:
            chosen_time = per_day_times.get(day.weekday(), default_time)
            candidate = datetime.combine(day, chosen_time, zone)
            if _is_valid_local_time(candidate, zone) and candidate > current:
                results.append(candidate)
        day += timedelta(days=1)
    return results


def to_youtube_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ScheduleError("Scheduled time must include a timezone.")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _is_valid_local_time(candidate: datetime, zone: ZoneInfo) -> bool:
    roundtrip = candidate.astimezone(timezone.utc).astimezone(zone)
    return (candidate.date(), candidate.hour, candidate.minute) == (
        roundtrip.date(), roundtrip.hour, roundtrip.minute
    )

