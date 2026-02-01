from dataclasses import replace

from game.components.spaceship import ShipTrail
from sparrow.core.components import Lifetime, PolygonRenderable
from sparrow.core.world import World


def trail_vfx_system(world: World) -> None:
    """
    Update the color and width of ship trails over their lifetime.
    """
    for eid, lt, poly, _ in world.join(Lifetime, PolygonRenderable, ShipTrail):
        ta = lt.time_alive
        t = ta / lt.duration
        current_alpha = 1.0 - t

        swap_threshold = 0.15

        if t < swap_threshold:
            mix = t / swap_threshold

            if mix < 0.5:
                local_mix = mix * 2.0
                r = 1.0
                g = (0.6 * (1 - local_mix)) + (1.0 * local_mix)
                b = (0.0 * (1 - local_mix)) + (1.0 * local_mix)
            else:
                local_mix = (mix - 0.5) * 2.0
                r = (1.0 * (1 - local_mix)) + (0.0 * local_mix)
                g = 1.0
                b = 1.0
        else:
            r, g, b = 0.0, 1.0, 1.0

        new_color = (r, g, b, current_alpha)
        new_width = max(0.5, 3.0 * current_alpha)

        world.add_component(
            eid, replace(poly, color=new_color, stroke_width=new_width)
        )
