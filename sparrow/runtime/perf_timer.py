import time
from typing import Optional

from moderngl_window.timers.base import BaseTimer


class PerfCounterTimer(BaseTimer):
    """Drop-in timer compatible with moderngl-window's timer API.

    Uses time.perf_counter() for high-resolution monotonic timing.
    """

    def __init__(self) -> None:
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None
        self._pause_time: Optional[float] = None
        self._last_frame = 0.0
        self._offset = 0.0
        self._frames = 0
        self._fps = 0.0

    @property
    def is_paused(self) -> bool:
        return self._pause_time is not None

    @property
    def is_running(self) -> bool:
        return self._pause_time is None

    @property
    def time(self) -> float:
        if self._start_time is None:
            return 0.0

        if self.is_paused and self._pause_time is not None:
            return self._pause_time - self._offset - self._start_time

        return time.perf_counter() - self._start_time - self._offset

    @time.setter
    def time(self, value: float) -> None:
        if value < 0:
            value = 0.0

        self._offset += self.time - value

    @property
    def fps_average(self) -> float:
        if self._frames == 0:
            return 0.0
        return self._frames / self.time

    @property
    def fps(self) -> float:
        return self._fps

    def next_frame(self) -> tuple[float, float]:
        self._frames += 1
        current = self.time
        delta, self._last_frame = current - self._last_frame, current

        if delta > 0:
            self._fps = 1.0 / delta
        else:
            self._fps = 0.0

        return current, delta

    def start(self) -> None:
        if self._start_time is None:
            self._start_time = time.perf_counter()
            self._last_frame = 0.0
        elif self._pause_time is not None:
            self._offset += time.perf_counter() - self._pause_time
            self._pause_time = None
        else:
            print("The timer is already started")

    def pause(self) -> None:
        self._pause_time = time.perf_counter()

    def toggle_pause(self) -> None:
        if self.is_paused:
            self.start()
        else:
            self.pause()

    def stop(self) -> tuple[float, float]:
        if self._start_time is None:
            return 0.0, 0.0

        self._stop_time = time.perf_counter()
        return (
            self._stop_time - self._start_time - self._offset,
            self._stop_time - self._start_time,
        )
