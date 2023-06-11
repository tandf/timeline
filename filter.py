from typing import List
import re


class FilterCond:
    # Disconjuntive normal form
    conds: List[List[str]]

    def __init__(self, conds: List[List[str]]) -> None:
        if conds is None:
            conds = []
        self.conds = conds
        self._normalize_conds()

    @classmethod
    def _normalize_cond(cls, cond: str) -> str:
        m = re.match("(!)?([#@])?(.*)", cond)
        assert m, f"Cannot recognize filter condition {cond}"

        neg, t, tag = m.groups()
        neg = "" if neg is None else neg
        t = "#" if t is None else t
        assert tag, f"No tag specified in filter condition {cond}"

        new_cond = neg + t + tag
        return new_cond

    def _normalize_conds(self) -> None:
        self.conds = [
            [self._normalize_cond(tag) for tag in cond]
            for cond in self.conds]

    def __str__(self) -> str:
        ands = ["(" + "/\\".join(c) + ")" for c in self.conds]
        return " \/ ".join(ands)

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def _filter_cond(cls, cond: List[str], tags: List[str]) -> bool:
        for c in cond:
            neg, tag = False, c
            if c[0] == "!":
                neg, tag = True, c[1:]

            if (tag in tags) == neg:
                return False

        return True

    def filter(self, tags: List[str]) -> bool:
        if not self.conds:
            return True
        for cond in self.conds:
            if self._filter_cond(cond, tags):
                return True
        return False
