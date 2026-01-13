# sparrow/graphics/frame_context.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(slots=True)
class FrameContext:
    """Per-frame transient counters and timing buckets."""

    timings_ms: Dict[str, float] = field(default_factory=dict)
    stats: Dict[str, int] = field(default_factory=dict)
