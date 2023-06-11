import yaml
from typing import List
import date_utils
from filter import FilterCond


class Config:
    name: str

    def __init__(self, raw_config: dict, path: str) -> None:
        self.start = date_utils.parse_date_str(raw_config["start"])
        self.end = date_utils.parse_date_str(raw_config["end"], self.start)
        self.path = path
        self.filter = FilterCond(
            raw_config["filter"] if "filter" in raw_config else None)

        for key, value in raw_config.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def __str__(self) -> str:
        return f"{self.name} ({self.start} - {self.end})"

    def __repr__(self) -> str:
        return self.__str__()


class ConfigDB:
    files: List[str]
    configs: List[Config]

    def __init__(self) -> None:
        self.files = []
        self.configs = []

    def load(self, path: str) -> None:
        self.files.append(path)

        # Read file and parse configs
        with open(path, "r") as f:
            configs = yaml.safe_load(f)
        try:
            for c in configs:
                self.configs.append(Config(c, path))
        except Exception as e:
            print(f"== Error when loading configs file {path} ==")
            raise e

    def __str__(self) -> str:
        sorted_configs = sorted(
            self.configs, key=lambda c: c.name)
        return "\n".join([str(c) for c in sorted_configs])

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    db = ConfigDB()
    db.load("data/configs/example.yaml")
    print(db)
