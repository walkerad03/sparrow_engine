# sparrow/graphics/ecs/events.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


@dataclass(frozen=True, slots=True)
class RenderFrameEvent:
    """
    Emitted once per frame.

    Intended consumers:
      - profiling overlays
      - frame capture tools
      - gameplay systems reacting to render timing (optional)
    """

    frame_index: int
    dt_seconds: float
    timings_ms: Mapping[str, float]  # pass_name -> GPU/CPU ms
    stats: Mapping[str, Any]  # implementation-defined counters


@dataclass(frozen=True, slots=True)
class RenderGraphChangedEvent:
    """
    Emitted when passes/resources are added/removed/recompiled.

    Useful for editor UI or debugging tools.
    """

    reason: Literal["pass_added", "pass_removed", "pass_replaced", "recompiled"]
    detail: str
