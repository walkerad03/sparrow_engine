# sparrow/debug/line.py

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, cast

from line_profiler import LineProfiler

logger = logging.getLogger("sparrow.profile.line")

P = ParamSpec("P")
R = TypeVar("R")


def line_profile(
    *,
    out_dir: Path,
    enabled: bool = True,
    target: Callable[..., Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Line profiling decorator using line_profiler.

    Args:
        out_dir: Directory to save the .lprof binary and readable .txt stats.
        enabled: Whether profiling is active.
        target: Optional specific function to profile line-by-line.
                If None, profiles the decorated function line-by-line.
                If provided, profiles ONLY this function's execution calls
                during the lifetime of the decorated function.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        if not enabled:
            return fn

        if LineProfiler is None:
            logger.warning(
                "line_profiler is not installed. Profiling disabled."
            )
            return fn

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            lp = LineProfiler()

            # Register the specific function(s) we want line-by-line stats for
            func_to_profile = target if target is not None else fn
            lp.add_function(func_to_profile)

            try:
                # Execute the decorated function through the profiler's trace function
                return lp.runcall(fn, *args, **kwargs)
            finally:
                out_dir.mkdir(parents=True, exist_ok=True)
                fn_name = cast(Any, fn).__name__
                base = fn_name

                if target is not None:
                    target_name = getattr(target, "__name__", "target")
                    base = f"{base}_target_{target_name}"

                lprof_path = out_dir / f"{base}.lprof"
                txt_path = out_dir / f"{base}.txt"

                # Dump the binary stats (viewable with standard line_profiler tools)
                lp.dump_stats(str(lprof_path))

                # Also dump a human-readable text file so you don't have to parse it manually
                with open(txt_path, "w", encoding="utf-8") as f:
                    lp.print_stats(stream=f)

                logger.info(
                    "Line profiling results for %s:", func_to_profile.__name__
                )
                logger.info("  Binary saved to: %s", lprof_path)
                logger.info("  Text saved to:   %s", txt_path)

        return wrapper

    return decorator
