from __future__ import annotations

import cProfile
import functools
import logging
import os
import pstats
import sys
import tracemalloc
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, cast

logger = logging.getLogger("sparrow.profile")

P = ParamSpec("P")
R = TypeVar("R")


def profile(
    *,
    out_dir: Path,
    enabled: bool = True,
    target: Callable[..., Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Profiling decorator.

    Args:
        out_dir: Directory to save profile stats.
        enabled: Whether profiling is active.
        target: Optional specific function to profile.
                If None, profiles the decorated function (usually main).
                If provided, profiles ONLY this function's execution calls
                aggregated over the lifetime of the decorated function.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        if not enabled:
            return fn

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            profiler = cProfile.Profile()
            active_target = target
            tracemalloc.start()

            def dump_stats():
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                out_dir.mkdir(parents=True, exist_ok=True)
                fn_name = cast(Any, fn).__name__
                base = fn_name

                if active_target is not None:
                    target_name = getattr(active_target, "__name__", "target")
                    base = f"{base}_target_{target_name}"

                prof_path = out_dir / f"{base}.prof"
                profiler.dump_stats(prof_path)

                try:
                    stats = pstats.Stats(str(prof_path))
                except (EOFError, TypeError):
                    logger.warning("No profile data collected.")
                    return

                for sort_key in ["tottime", "cumtime", "calls"]:
                    path = out_dir / f"{base}.{sort_key}.txt"
                    with open(path, "w") as f:
                        ps = pstats.Stats(str(prof_path), stream=f)
                        ps.sort_stats(sort_key).print_stats(50)

                frame_count = 0
                update_count = 0
                wait_time = 0.0

                internal_stats = getattr(stats, "stats", {})
                for (file_path, _, name), (
                    _,
                    nc,
                    tt,
                    _,
                    _,
                ) in internal_stats.items():
                    if name == "next_frame":
                        frame_count += nc
                        wait_time += tt
                    elif name == "update_fixed":
                        file_name = os.path.basename(file_path)
                        if file_name == "scene.py":
                            update_count += nc

                total_time = getattr(stats, "total_tt", 0)
                peak_mb = peak / 1024 / 1024
                net_mb = current / 1024 / 1024

                logger.info("Profiling results for %s:", fn_name)
                logger.info("  Runtime: %.4fs", total_time)
                logger.info(
                    "  Memory: Peak %.2fMB | Net Change %+.2fMB",
                    peak_mb,
                    net_mb,
                )

                if frame_count > 0:
                    fps = frame_count / total_time
                    ups = update_count / total_time
                    cpu_work_time = total_time - wait_time
                    avg_work_ms = (cpu_work_time / frame_count) * 1000
                    wait_percent = (wait_time / total_time) * 100
                    mem_per_frame_kb = (
                        (current / frame_count) / 1024 if current > 0 else 0
                    )

                    logger.info("  Performance: %.2f FPS | %.2f UPS", fps, ups)
                    logger.info(
                        "  Frame Speed: Work/Frame: %.2fms | V-Sync Idle: %.1f%%",
                        avg_work_ms,
                        wait_percent,
                    )

                    if mem_per_frame_kb > 0.1:
                        logger.warning(
                            "  Frame Leakage detected: ~%.2f KB/frame",
                            mem_per_frame_kb,
                        )
                else:
                    logger.info(
                        "  No 'swap_buffers' detected; frame metrics unavailable."
                    )

                logger.info("Detailed traces saved to: %s", out_dir)

            if target is None:
                profiler.enable()
                try:
                    return fn(*args, **kwargs)
                finally:
                    profiler.disable()
                    dump_stats()
            else:
                # Targeted Mode: Patch 'target' to toggle profiler on/off
                target_any = cast(Any, target)
                module = sys.modules[target_any.__module__]
                qualname = target_any.__qualname__.split(".")

                owner = module
                for part in qualname[:-1]:
                    owner = getattr(owner, part)

                method_name = qualname[-1]
                original_target = getattr(owner, method_name)

                @functools.wraps(original_target)
                def interceptor(*t_args, **t_kwargs):
                    profiler.enable()
                    try:
                        return original_target(*t_args, **t_kwargs)
                    finally:
                        profiler.disable()

                setattr(owner, method_name, interceptor)
                try:
                    return fn(*args, **kwargs)
                finally:
                    setattr(owner, method_name, original_target)
                    dump_stats()

        return wrapper

    return decorator
