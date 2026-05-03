from dataclasses import dataclass

from sparrow.ecs import World
from sparrow.input.resources import InputState


@dataclass
class SpawnCubeRequest:
    """Event: Requested to spawn a cube."""

    pass


def game_input_system(world: World) -> None:
    """
    Game-level input system that utilizes the event bus.

    This system runs before the engine's input system to catch 'one-shot'
    key presses like 'E' for spawning. It re-emits events so that the
    engine's InputState (used by freecam) remains accurate.
    """
    input_state = world.res_get(InputState)
    if not input_state:
        return

    if input_state.is_action_pressed("mouse_left_click"):
        world.event_add(SpawnCubeRequest())
