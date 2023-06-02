from typing import List
import yaml
import datetime
import os
import date_utils


class EventTime:

    def __init__(self, time, last_date: datetime.date) -> None:
        self.start = None
        self.end = None
        self.date = None

        self.raw_time = time

        if isinstance(time, str):
            self.date = date_utils.parse_date(time, last_date)

        elif isinstance(time, dict):
            if "start" in time:
                self.start = date_utils.parse_date(time["start"], last_date)
            else:
                # If start time not specified, use last date
                assert last_date is not None
                self.start = last_date

            assert "end" in time, f"Event end time not specified."
            self.end = date_utils.parse_date(time["end"], self.start)

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

    def load(self, path: str, update: bool = False) -> None:
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
            print(f"== Error when loading events file {path} ==")
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
    db.load("data/events/example.yaml")
    print(db)
