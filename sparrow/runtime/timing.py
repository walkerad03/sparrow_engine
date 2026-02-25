# sparrow/runtime/timing.py
from dataclasses import dataclass

import moderngl_window as mglw


@dataclass
class FixedStep:
    target_ups: int
    target_fps: int  # TODO: Find a good way to support this.
    timer: mglw.timers.clock.Timer
    max_frame_time: float = 1.0
    max_steps_per_frame: int = 16

    _dt: float = 0.0
    _last_time: float = 0.0
    _accum: float = 0.0

    _render_dt: float = 0.0
    _last_render_time: float = 0.0

    def __post_init__(self):
        self._dt = 1.0 / self.target_ups

    def start(self) -> None:
        """Call this right before the main loop starts."""
        self._last_time = self.timer.time
        self._accum = 0.0

    def advance(self) -> int:
        """
        Advances the timer and returns how many fixed steps
        should be run this frame.
        """
        now = self.timer.time
        frame_time = now - self._last_time
        self._last_time = now

        # Prevent spiral of death (lag causing more lag)
        if frame_time > self.max_frame_time:
            frame_time = self.max_frame_time

        self._accum += frame_time

        steps = 0
        while self._accum >= self._dt and steps < self.max_steps_per_frame:
            self._accum -= self._dt
            steps += 1

        # If we are still behind after max steps, discard the accumulated time
        # to prevent catching up in a "fast-forward" motion.
        if steps >= self.max_steps_per_frame:
            self._accum = 0.0

        return steps

    @property
    def dt(self) -> float:
        """The fixed delta time (e.g., 0.0166 for 60fps)."""
        return self._dt

    @property
    def alpha(self) -> float:
        """
        Normalized value (0.0 to 1.0) representing how far we are
        between the last fixed step and the next one.
        Useful for interpolating positions during rendering.
        """
        return self._accum / self._dt
