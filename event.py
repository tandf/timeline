from typing import List
import yaml
import datetime
import os
import re
import math


class EventTime:
    @classmethod
    def next_month_day(cls, since: datetime.date, month: int, day: int) -> datetime.date:
        year = since.year
        while True:
            try:
                date = datetime.datetime(year, month, day).date()
                if date > since:
                    return date
            except ValueError:
                pass
            year += 1

    @classmethod
    def time_delta(cls, base: datetime.date, delta_str: str):
        match = re.match(r"\+(\d+)([dwmy])", delta_str.lower())
        if not match:
            raise ValueError(f"Cannot parse date delta {delta_str}")

        assert base is not None, f"Cannot find base for {delta_str}"

        number = int(match.group(1))
        unit_char = match.group(2)
        if unit_char == "d":
            return base + datetime.timedelta(days=number)
        elif unit_char == "w":
            return base + datetime.timedelta(weeks=number)
        else:
            if unit_char == "m":
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
                date_base = base + datetime.timedelta(days=-compensate)
                return date_base.replace(year=new_year, month=new_month)
            except ValueError:
                pass
            compensate += 1

        raise Exception(f"Cannot add time delta {delta_str} to {base}")

    @classmethod
    def parse_date(cls, date_str: str, last_date: datetime.date) -> datetime.date:
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

        # e.g. +5d, +4w, +2m
        if date_str.strip().startswith("+"):
            return EventTime.time_delta(last_date, date_str)

        # e.g. May 04
        try:
            date = datetime.datetime.strptime(formatted_str, "%b %d").date()
            return EventTime.next_month_day(last_date, date.month, date.day)
        except ValueError:
            # Handle Feb 29
            if formatted_str == "Feb 29":
                return EventTime.next_month_day(last_date, 2, 29)

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

        raise ValueError(f"Cannot parse date {date_str}")

    def __init__(self, time, last_date: datetime.date) -> None:
        self.start = None
        self.end = None
        self.date = None

        self.raw_time = time

        if isinstance(time, str):
            self.date = EventTime.parse_date(time, last_date)

        elif isinstance(time, dict):
            if "start" in time:
                self.start = EventTime.parse_date(time["start"], last_date)
            else:
                # If start time not specified, use last date
                assert last_date is not None
                self.start = last_date

            assert "end" in time, f"Event end time not specified."
            self.end = EventTime.parse_date(time["end"], self.start)

        else:
            raise TypeError(f"Unknown event time: {time}")

    def _sanity_check(self) -> None:
        assert (self.start is None) == (self.end is None)
        assert (self.start is None) != (self.date is None)

    def isPeriod(self) -> bool:
        self._sanity_check()
        return self.start is not None

    def isTime(self) -> bool:
        self._sanity_check()
        return self.date is not None

    def getStartTime(self) -> datetime.date:
        self._sanity_check()
        if self.isPeriod():
            return self.start
        else:
            return self.date

    def getEndTime(self) -> datetime.date:
        self._sanity_check()
        if self.isPeriod():
            return self.end
        else:
            return self.date

    def __str__(self) -> str:
        if self.isPeriod():
            return f"{self.start} - {self.end}"
        else:
            return f"{self.date}"

    def __repr__(self) -> str:
        return self.__str__()


class Event:
    name: str
    description: str
    tags: List[str]
    file: str
    time: EventTime

    def __init__(self, raw_event: dict, file: str, last_date: datetime.date = None) -> None:
        assert "name" in raw_event, f"Event w/o name in file {file}"
        self.name = raw_event["name"]

        self.description = ""
        if "description" in raw_event:
            self.description = raw_event["description"]

        self.tags = []
        if "tags" in raw_event:
            self.tags = [f"#{t}" for t in raw_event["tags"]]

        self.file = file
        self.tags.append(f"@{os.path.splitext(os.path.basename(file))[0]}")

        assert "time" in raw_event, f"Event w/o time in file {file}"
        self.time = EventTime(raw_event["time"], last_date)

    def filter_tags(self, tags: List[str]) -> List[str]:
        # Return a list of tags that match with this event
        assert isinstance(tags, list)
        return list(set(self.tags).intersection(set(tags)))

    def filter_dates(self, start: datetime.date, end: datetime.date) -> bool:
        return True

    def __str__(self) -> str:
        return f"{self.name} ({self.time}) [{' '.join(sorted(self.tags))}]"

    def __repr__(self) -> str:
        return self.__str__()


class EventDB:
    files: List[str]
    events: List[Event]

    def __init__(self) -> None:
        self.files = []
        self.events = []

    def parse(self, path: str, update: bool = False) -> None:
        self.files.append(path)

        # Read file and parse events
        with open(path, "r") as f:
            events = yaml.safe_load(f)
        last_date = None
        try:
            for e in events:
                event = Event(e, path, last_date)
                self.events.append(event)
                last_date = event.time.getEndTime()
        except Exception as e:
            print(f"== Error when reading events file {path} ==")
            raise e

        # TODO: Back up and update the events file

    def filter_tags(self, tags: List[str]) -> List[Event]:
        # Return a list of events matching the tags
        return [e for e in self.events if e.filter_tags(tags)]

    def __str__(self) -> str:
        sorted_events = sorted(
            self.events, key=lambda e: e.time.getStartTime())
        return "\n".join([str(e) for e in sorted_events])

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    EventTime("Jan 1", None)
    EventTime("Feb 29", None)
    EventTime("Feb 29", datetime.date(2002, 2, 3))
    EventTime("May 4 2023", None)
    EventTime("05/04/2023", None)
    EventTime("2023 May 4", None)
    EventTime("2023/05/04", None)
    EventTime({"start": "May 4", "end": "May 9"}, None)

    db = EventDB()
    db.parse("data/events/example.yaml")
    print(db)
