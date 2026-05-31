def parse_hhmm(value: str) -> int:
    if not isinstance(value, str) or ":" not in value:
        raise ValueError(f"Invalid time format: {value!r}")
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {value!r}")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid time format: {value!r}")
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        raise ValueError(f"Invalid time format: {value!r}")
    return hour * 60 + minute


def format_minutes(minutes: int) -> str:
    if not isinstance(minutes, int) or minutes < 0:
        raise ValueError(f"Invalid minutes: {minutes!r}")
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"
