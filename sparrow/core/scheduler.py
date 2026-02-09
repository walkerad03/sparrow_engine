from __future__ import annotations

from enum import Enum, auto
from graphlib import TopologicalSorter
from typing import Callable, Dict, List, Union

from sparrow.core.world import World
from sparrow.types import SystemId


class Stage(Enum):
    STARTUP = auto()  # Run once on scene start
    INPUT = auto()  # Poll input
    UPDATE = auto()  # Game logic (AI, scripts)
    PHYSICS = auto()  # Movement integration, collision
    POST_UPDATE = auto()  # Camera follow, cleanup
    RENDER = auto()  # Extraction to RenderFrame


SystemFn = Callable[[World], None]


class Scheduler:
    def __init__(self):
        self._registered_systems = []

        self._execution_order: Dict[Stage, List[SystemFn]] = {
            s: [] for s in Stage
        }
        self._is_compiled = False

    def add_system(
        self,
        stage: Stage,
        system: SystemFn,
        name: Union[SystemId, None] = None,
        before: Union[SystemId, List[SystemId], None] = None,
        after: Union[SystemId, List[SystemId], None] = None,
    ) -> None:
        """Register a simple function as a system."""
        if self._is_compiled:
            raise RuntimeError(
                "Cannot add systems after scheduler is compiled."
            )

        name_attr = getattr(system, "__name__")
        sys_name = name or SystemId(name_attr)

        before_deps = [before] if isinstance(before, str) else (before or [])
        after_deps = [after] if isinstance(after, str) else (after or [])

        self._registered_systems.append(
            {
                "stage": stage,
                "func": system,
                "name": sys_name,
                "before": before_deps,
                "after": after_deps,
            }
        )

    def compile(self) -> None:
        by_stage = {s: [] for s in Stage}
        for entry in self._registered_systems:
            by_stage[entry["stage"]].append(entry)

        for stage, entries in by_stage.items():
            sorter = TopologicalSorter()

            name_map = {}

            for entry in entries:
                name = entry["name"]
                name_map[name] = entry["func"]
                sorter.add(name, *entry["after"])

            for entry in entries:
                name = entry["name"]
                for successor in entry["before"]:
                    sorter.add(successor, name)

            try:
                sorted_names = list(sorter.static_order())
            except Exception as e:
                raise RuntimeError(
                    f"Cycle detected or dependency error in stage {stage.name}: {e}"
                )

            final_list = []
            for name in sorted_names:
                if name in name_map:
                    final_list.append(name_map[name])

            self._execution_order[stage] = final_list

        self._is_compiled = True

    def run_stage(self, stage: Stage, world: World) -> None:
        if not self._is_compiled:
            self.compile()

        for system in self._execution_order[stage]:
            system(world)

    def clear(self):
        for stage in Stage:
            self._execution_order[stage].clear()

        self._is_compiled = False
