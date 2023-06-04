import datetime
from event import EventDB, Event
from config import ConfigDB, Config
import os
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict
import textwrap
import date_utils
import argparse


class Timeline:
    fig: Figure
    config: Config

    # 10 colors should be enough
    track_colors = ["#dbacac", "#a2c9aa", "#909eb4", "#b06262", "#605e5e",
                    "#f8c758", "#bdeff6", "#5ec6ec", "#70d4c0", "#9d725e"]

    default_date_vline_style = {"color": "red", "linewidth": 3}
    default_date_text_style = {"color": "red", "ha": "center", "va": "bottom",
                          "fontsize": 18}

    def __init__(self, config: Config) -> None:
        self.fig = None
        self.config = config

        if hasattr(self.config, "width") and hasattr(self.config, "height"):
            self.width = self.config.width
            self.height = self.config.height
        else:
            self.width, self.height = 16, 9
        self.Xmin = 0
        self.Ymin = 0
        self.Xmax = self.Xmin + self.width
        self.Ymax = self.Ymin + self.height

    def __del__(self):
        if self.fig:
            plt.close(self.fig)
            self.fig = None

    def set_events(self, events: List[Event]) -> None:
        self.events = events
        tags = set(tag for e in self.events for tag in e.tags)
        self.tracks = sorted(tag for tag in tags if tag.startswith("@"))
        self.track_cnt = len(self.tracks)
        self._draw_init()

    def _draw_init(self) -> None:
        if self.fig:
            plt.close(self.fig)
        self.fig = plt.figure(figsize=(self.width, self.height))
        plt.xlim((self.Xmin, self.Xmax + 0.01))  # TODO
        plt.ylim((self.Ymin, self.Ymax))
        plt.axis('off')
        plt.tight_layout()

        self.caption_padding = 0.1
        self.legend_padding = 0.15
        self.timeline_height = 1 - self.caption_padding - self.legend_padding
        self.track_height = min(self.timeline_height / self.track_cnt, 0.15)

        by_y = self.Ymin + self.legend_padding * self.height
        bg_height = self.height * \
            (1 - self.legend_padding - self.caption_padding)
        rect = plt.Rectangle((self.Xmin, by_y), self.width, bg_height,
                             fill=False, ls="--", linewidth=1, edgecolor="grey")
        plt.gca().add_patch(rect)

    def _get_track_y(self, track_num: int) -> float:
        return (1 - (self.caption_padding + self.track_height * track_num)) * \
            self.height + self.Ymin

    def _get_date_x(self, date: datetime.date) -> float:
        return (date - self.config.start) / \
            (self.config.end - self.config.start) * \
            self.width + self.Xmin

    def _get_text_extent(self, text):
        renderer = self.fig.canvas.get_renderer()
        extent = text.get_window_extent(renderer=renderer)
        transformed_bbox = extent.transformed(
            self.fig.gca().transData.inverted())
        return transformed_bbox

    def _draw_text_in_box(self, text: str, center_x: float, center_y: float,
                         width: float, height: float, breakline: bool = True,
                         max_fontsize: float = 18) -> Text:
        fontsize = max_fontsize
        txt = plt.text(center_x, center_y, text, ha='center', va='center')
        while fontsize > 0:
            txt.set_fontsize(fontsize)
            extent = self._get_text_extent(txt)
            text_width, text_height = extent.width, extent.height
            if text_width <= width and text_height <= height:
                return txt

            if breakline and text_width > width and text_height <= height:
                line_cnt = 2
                while line_cnt < 4 and text_height <= height:
                    new_text = "\n".join(textwrap.wrap(
                        text, width=len(text)/line_cnt, break_long_words=False))
                    txt.set_text(new_text)
                    extent = self._get_text_extent(txt)
                    text_width, text_height = extent.width, extent.height
                    if text_width <= width and text_height <= height:
                        return txt
                    line_cnt += 1
                txt.set_text(text)

            fontsize -= 1

    def _draw_box_text_impl(self, text: str, left: float, bottom: float,
                            width: float, height: float, color):
        rect = plt.Rectangle((left, bottom), width, height, facecolor=color,
                             linewidth=1, edgecolor="#1e2725")
        plt.gca().add_patch(rect)

        if text is not None:
            txt = self._draw_text_in_box(text, left+width/2, bottom+(height)/2,
                                         width*.95, height*.95)

        return rect, txt

    def _draw_event_period(self, event: Event) -> Tuple[Rectangle, Text]:
        start, end = event.time.date_intersection(self.config.start,
                                                  self.config.end)
        track_num = self.tracks.index(event.get_track())
        color = self.track_colors[track_num]

        left = self._get_date_x(start)
        right = self._get_date_x(end)
        top = self._get_track_y(track_num)
        bottom = top - self.track_height * self.height
        width = right - left
        height = top - bottom

        return self._draw_box_text_impl(event.name, left, bottom, width, height,
                                        color)

    def _draw_date_impl(self, text: str, x: float, text_y_offset: float = 0.05,
                        ymin: float = None, ymax: float = None,
                        vline_style: dict = None, text_style: dict = None):
        if ymin is None:
            ymin = self.legend_padding
        if ymax is None:
            ymax = 1 - self.caption_padding

        if vline_style is None:
            vline_style = {}
        vline_style = {**self.default_date_vline_style, **vline_style}

        if text_style is None:
            text_style = {}
        text_style = {**self.default_date_text_style, **text_style}

        vline = plt.axvline(x=x, ymin=ymin, ymax=ymax, **vline_style)
        txt = plt.text(x, (ymax+text_y_offset)*self.height, text, **text_style)

        return vline, txt

    def _draw_event_date(self, event: Event) -> None:
        x = self._get_date_x(event.time.date)
        self._draw_date_impl(event.name, x)

    def draw_events(self) -> None:
        for event in self.events:
            if event.time.isPeriod():
                self._draw_event_period(event)
            else:
                self._draw_event_date(event)

    def draw_today(self, today: datetime.date = None) -> None:
        if today is None:
            today = datetime.date.today()
        if today < self.config.start or today > self.config.end:
            print(f"WARNING: {today} is out of range of the timeline "
                  f"({self.config.start} - {self.config.end})")
            return
        x = self._get_date_x(today)
        self._draw_date_impl("Today", x, 0.01)

    def draw_grid(self, weekday: int = 0, period: int = 7) -> None:
        date = date_utils.next_weekday(
            self.config.start - datetime.timedelta(days=1), weekday)

        while date < self.config.end:
            x = self._get_date_x(date)
            _, txt = self._draw_date_impl(
                date.strftime("%b %d"), x, text_y_offset=0.01,
                vline_style={"color": "grey",
                             "linewidth": 1, "ls": "--", "zorder": 0},
                text_style={"color": "grey", "fontsize": 16},
            )

            extent = self._get_text_extent(txt)
            text_width, _ = extent.width, extent.height
            text_x, _ = txt.get_position()
            if text_x - text_width / 2 < self.Xmin or \
                    text_x + text_width / 2 > self.Xmax:
                txt.remove()

            date += datetime.timedelta(days=period)

    def draw_legend(self, track_names: Dict[str, str]) -> None:
        max_height = (self.legend_padding - 0.03) * self.height
        max_width = 0.15 * self.width
        ratio = 3  # width : height
        padding = 0.03 * self.width
        bottom = 0.01 * self.height + self.Ymin

        width = (self.width - padding * (self.track_cnt + 1)) / self.track_cnt
        width = min(max_width, width)
        height = width / ratio
        if height > max_height:
            height = max_height
            width = height * ratio

        legend_width = padding * (self.track_cnt - 1) + width * self.track_cnt
        center = self.Xmin + self.width / 2

        for idx, track in enumerate(self.tracks):
            left = center - legend_width / 2 + (padding + width) * idx
            track_name = track_names[track]
            color = self.track_colors[idx]
            self._draw_box_text_impl(track_name, left, bottom, width, height,
                                     color)

    def dump(self, dir: str) -> None:
        output_file = os.path.join(dir, self.config.filename)
        _, ext = os.path.splitext(output_file)
        if not ext:
           output_file += ".png"
        plt.savefig(output_file, bbox_inches="tight")


def parse_args():
    parser = argparse.ArgumentParser(description="Timeline")
    parser.add_argument("--events", type=str, help="path to the events dir")
    parser.add_argument("--configs", type=str,
                        help="path to the config file, or dir of configs")
    parser.add_argument("--out", type=str, help="output dir")
    parser.add_argument("--today", type=str, help="draw today [date]")
    parser.add_argument("working_dir", nargs="?", type=str, default=".")
    opt = parser.parse_args()
    return opt


def main():
    eventDB = EventDB()
    configDB = ConfigDB()

    opt = parse_args()

    if opt.configs is not None:
        config_dir = opt.configs
    else:
        config_dir = os.path.join(opt.working_dir, "configs")

    if opt.events is not None:
        event_dir = opt.events
    else:
        event_dir = os.path.join(opt.working_dir, "events")

    if opt.out is not None:
        out_dir = opt.out
    else:
        out_dir = os.path.join(opt.working_dir, "out")
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    for file in os.listdir(config_dir):
        if file.endswith(".yaml") or file.endswith(".yml"):
            configDB.load(os.path.join(config_dir, file))

    for file in os.listdir(event_dir):
        if file.endswith(".yaml") or file.endswith(".yml"):
            eventDB.load(os.path.join(event_dir, file))

    today = None
    if opt.today is not None:
        today = date_utils.parse_date(None, opt.today)
        assert today is not None, f"Cannot parse date {opt.today}"

    for config in configDB.configs:
        timeline = Timeline(config)
        timeline.set_events(eventDB.filter(
            config.tags, config.start, config.end))
        timeline.draw_events()
        timeline.draw_today(today)
        timeline.draw_grid(period=14)
        timeline.draw_legend(eventDB.track_names)

        config_out = os.path.join(out_dir, os.path.basename(config.path))
        if not os.path.isdir(config_out):
            os.mkdir(config_out)
        timeline.dump(config_out)

if __name__ == "__main__":
    main()
