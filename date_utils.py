import datetime
import math
import re


def next_month_day(since: datetime.date, month: int, day: int) -> datetime.date:
    year = since.year
    while True:
        try:
            date = datetime.datetime(year, month, day).date()
            if date >= since:
                return date
        except ValueError:
            pass
        year += 1


def next_weekday(since: datetime.date, weekday: int) -> datetime.date:
    days = (weekday + 7 - since.weekday()) % 7
    return since + datetime.timedelta(days=days)


def _parse_delta(base: datetime.date, sign, number, unit) -> datetime.date:
    if unit == "d":
        return base + datetime.timedelta(days=number) * sign
    elif unit == "w":
        return base + datetime.timedelta(weeks=number) * sign
    else:
        if unit == "m":
            new_year = math.floor(number / 12) + base.year
            new_month = number % 12 + base.month
        else:  # "y"
            new_year = number + base.year
            new_month = base.month
        if new_month > 12:
            new_month -= 12
            new_year += 1

        compensate = 0  # Handle months with 31 days -> 30/29/28
        while compensate <= 3:
            try:
                date_base = base + datetime.timedelta(days=-compensate) * sign
                return date_base.replace(year=new_year, month=new_month)
            except ValueError:
                pass
            compensate += 1


def parse_delta(base: datetime.date, delta_str: str):
    if not re.match(r"([+-])(\d+)([dwmy])+", delta_str.lower()):
        return None

    date = base
    if date is None:
        date = datetime.date.today()

    matches = re.findall(r"([+-])(\d+)([dwmy])+", delta_str.lower())
    for parts in matches:
        sign = -1 if parts[0] == "-" else 1
        number = int(parts[1])
        unit_char = parts[2]
        date = _parse_delta(date, sign, number, unit_char)
    return date


def parse_date(last_date: datetime.date, date_str: str) -> datetime.date:
    # Replace comma
    seps = [",", "-", "/"]
    formatted_str = date_str
    for sep in seps:
        formatted_str = formatted_str.replace(sep, " ")
    # Remove extra whitespaces
    formatted_str = " ".join(formatted_str.split())

    if last_date is None:
        # Set the end of last year as the last date
        last_date = datetime.date(
            year=datetime.date.today().year, month=1, day=1)
        last_date -= datetime.timedelta(days=1)

    # e.g. May 04
    try:
        date = datetime.datetime.strptime(formatted_str, "%b %d").date()
        return next_month_day(last_date, date.month, date.day)
    except ValueError:
        # Handle Feb 29
        if formatted_str == "Feb 29":
            return next_month_day(last_date, 2, 29)

    format_strs = [
        "%b %d %Y",  # e.g. May 4, 2023
        "%m %d %Y",  # e.g. 05/04/2023
        "%Y %b %d",  # e.g. 2023 May 4
        "%Y %m %d",  # e.g. 2023/05/04
    ]
    for format_str in format_strs:
        try:
            return datetime.datetime.strptime(formatted_str, format_str).date()
        except ValueError:
            pass

    return None


def parse_date_str(date_str: str, last_date: datetime.date = None) -> datetime.date:
    # e.g. +5d, +4w, +2m
    date = parse_delta(last_date, date_str)
    if date:
        return date

    date = parse_date(last_date, date_str)
    if date:
        return date

    raise ValueError(f"Cannot parse date {date_str}")
