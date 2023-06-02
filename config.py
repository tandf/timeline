import yaml
from typing import List
import date_utils


class Config:
    name: str
    tags: List[str]

    def __init__(self, raw_config: dict) -> None:
        self.name = raw_config["name"]
        self.tags = raw_config["tags"]
        self.start = date_utils.parse_date(raw_config["start"])
        self.end = date_utils.parse_date(raw_config["end"])

    def __str__(self) -> str:
        return f"{self.name} ({self.start} - {self.end}) [{' '.join(sorted(self.tags))}]"

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
                self.configs.append(Config(c))
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
