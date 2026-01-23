from __future__ import annotations

import cProfile
import functools
import io
import pstats
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def profile(*, out_dir: Path, enabled: bool = True):
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        if not enabled:
            return fn

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            profiler = cProfile.Profile()
            profiler.enable()
            try:
                return fn(*args, **kwargs)
            finally:
                profiler.disable()

                out_dir.mkdir(parents=True, exist_ok=True)
                base = fn.__name__
                prof_path = out_dir / f"{base}.prof"

                profiler.dump_stats(prof_path)
                print(f"[profile] wrote {prof_path}")

                stats = pstats.Stats(profiler)

                cmds: list[str] = ["tottime", "cumtime", "calls"]
                paths: list[Path] = [out_dir / f"{base}.{x}.txt" for x in cmds]

                for path, cmd in zip(paths, cmds):
                    buf = io.StringIO()
                    stats = pstats.Stats(profiler, stream=buf)
                    stats.sort_stats(cmd).print_stats(30)
                    path.write_text(buf.getvalue())
                    print(f"[profile] wrote {path}")

                frame_count = 0
                for (_, _, name), (
                    cc,
                    nc,
                    tt,
                    ct,
                    callers,
                ) in stats.stats.items():
                    if name in (
                        "<built-in method pygame.display.flip>",
                        "<built-in method pygame.display.update>",
                    ):
                        frame_count += nc

                total_time = stats.total_tt
                fps = frame_count / total_time if total_time > 0 else 0

                print(f"[profile] Total Time: {total_time:.4f}s")
                print(f"[profile] Average FPS: {fps:.2f}")

                print("[profile] profiling complete")

        return wrapper

    return decorator
