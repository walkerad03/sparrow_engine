# sparrow/debug/logger.py
import logging
from pathlib import Path


class SparrowFormatter(logging.Formatter):
    """Custom formatter to handle fixed-width columns and name cropping."""

    def __init__(self, name_width: int = 20):
        super().__init__("%(levelname)-8s %(bracketed_name)s %(message)s")
        self.name_width = name_width

    def format(self, record):
        name = record.name
        max_name_len = self.name_width - 2
        if len(name) > max_name_len:
            display_name = name[: max_name_len - 1] + "…"
        else:
            display_name = name
        record.bracketed_name = f"[{display_name}]".ljust(self.name_width)
        return super().format(record)


def setup_logging():
    debug_dir = Path(".debug")
    debug_dir.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(SparrowFormatter(name_width=20))
    # root.addHandler(console_handler)

    file_handler = logging.FileHandler(debug_dir / "engine_raw.log", mode="w")
    raw_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(raw_formatter)
    root.addHandler(file_handler)
