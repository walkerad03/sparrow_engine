from dataclasses import replace

from game.components.screen_fade import ScreenFade
from sparrow.core.components import Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.renderer import Renderer
from sparrow.types import EntityId


def screen_fade_system(world: World, dt: float, renderer: Renderer) -> None:
    """
    Updates fade timers and syncs the 'Curtain' position to the camera.
    """
    finished_entities: list[EntityId] = []

    camera = renderer.camera

    for eid, fade, sprite, trans in world.join(ScreenFade, Sprite, Transform):
        assert (
            isinstance(fade, ScreenFade)
            and isinstance(sprite, Sprite)
            and isinstance(trans, Transform)
        )
        fade.timer += dt

        progress = min(fade.timer / fade.duration, 1.0)

        alpha = 1.0
        if fade.fade_type == "in":
            # Fade In: Starts at 1.0 (Black), goes to 0.0 (Clear)
            alpha = 1.0 - progress
        else:
            # Fade Out: Starts at 0.0 (Clear), goes to 1.0 (Black)
            alpha = progress

        r, g, b, _ = sprite.color
        next_sprite = replace(sprite, color=(r, g, b, alpha))
        world.mutate_component(eid, next_sprite)

        next_trans = replace(trans, x=camera.position[0], y=camera.position[1])
        world.mutate_component(eid, next_trans)

        if progress >= 1.0:
            if fade.fade_type == "in":
                finished_entities.append(eid)

    for eid in finished_entities:
        world.delete_entity(eid)
