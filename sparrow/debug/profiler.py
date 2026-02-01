from __future__ import annotations

import cProfile
import functools
import io
import pstats
import sys
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, cast

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

            def dump_stats():
                out_dir.mkdir(parents=True, exist_ok=True)

                fn_any = cast(Any, fn)
                base = fn_any.__name__

                if target:
                    target_any = cast(Any, target)
                    base += f"_target_{target_any.__name__}"

                prof_path = out_dir / f"{base}.prof"

                profiler.dump_stats(prof_path)
                print(f"[profile] wrote {prof_path}")

                try:
                    stats = pstats.Stats(str(prof_path))
                except (EOFError, TypeError):
                    print("[profile] Warning: No data collected.")
                    return

                cmds: list[str] = ["tottime", "cumtime", "calls"]
                paths: list[Path] = [out_dir / f"{base}.{x}.txt" for x in cmds]

                for path, cmd in zip(paths, cmds):
                    buf = io.StringIO()
                    stats_stream = pstats.Stats(str(prof_path), stream=buf)
                    stats_stream.sort_stats(cmd).print_stats(30)
                    path.write_text(buf.getvalue())
                    print(f"[profile] wrote {path}")

                # FPS Calculation (heuristic uses pygame func calls)
                frame_count = 0
                internal_stats = getattr(stats, "stats", {})
                for (_, _, name), (_, nc, _, _, _) in internal_stats.items():
                    if name in (
                        "<built-in method pygame.display.flip>",
                        "<built-in method pygame.display.update>",
                    ):
                        frame_count += nc

                total_time = getattr(stats, "total_tt", 0)
                fps = frame_count / total_time if total_time > 0 else 0

                print(f"[profile] Total Time: {total_time:.4f}s")
                if frame_count > 0:
                    print(f"[profile] Average FPS: {fps:.2f}")
                print("[profile] profiling complete")

            if target is None:
                profiler.enable()
                try:
                    return fn(*args, **kwargs)
                finally:
                    profiler.disable()
                    dump_stats()
            else:
                # Targeted Mode: Patch 'target' to toggle profiler on/off
                @functools.wraps(target)
                def target_interceptor(*t_args, **t_kwargs):
                    profiler.enable()
                    try:
                        return original_target(*t_args, **t_kwargs)
                    finally:
                        profiler.disable()

                target_any = cast(Any, target)
                owner_name = target_any.__module__
                owner = sys.modules[owner_name]
                path_parts = target_any.__qualname__.split(".")

                for part in path_parts[:-1]:
                    owner = getattr(owner, part)
                method_name = path_parts[-1]

                original_target = getattr(owner, method_name)
                setattr(owner, method_name, target_interceptor)

                print(
                    f"[profile] Patching {target_any.__qualname__} for targeted profiling"
                )

                try:
                    return fn(*args, **kwargs)
                finally:
                    setattr(owner, method_name, original_target)
                    dump_stats()

        return wrapper

    return decorator
