import numpy as np

from game.components.spaceship import ShipTrail
from sparrow.core.components import Lifetime, PolygonRenderable
from sparrow.core.world import World


def trail_vfx_system(world: World) -> None:
    """
    Update the color and width of ship trails over their lifetime.
    """
    for count, (lts, polys, _) in world.get_batch(
        Lifetime, PolygonRenderable, ShipTrail
    ):
        if count == 0:
            continue

        time_alive = lts["time_alive"]
        duration = lts["duration"]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (time_alive / duration).flatten()
            t = np.clip(t, 0.0, 1.0)

        current_alpha = 1.0 - t
        polys["color"][:, 3] = current_alpha

        width_values = np.maximum(0.5, 3.0 * current_alpha)
        polys["stroke_width"] = width_values[:, None]

        swap_threshold = 0.15

        mask_a = t < (swap_threshold * 0.5)
        mask_b = (t >= (swap_threshold * 0.5)) & (t < swap_threshold)
        mask_c = t >= swap_threshold

        if np.any(mask_a):
            t_subset = t[mask_a]
            local_mix = t_subset / (swap_threshold * 0.5)

            polys["color"][mask_a, 0] = 1.0
            polys["color"][mask_a, 1] = 0.6 + (0.4 * local_mix)
            polys["color"][mask_a, 2] = local_mix

        if np.any(mask_b):
            t_subset = t[mask_b]
            mix = t_subset / swap_threshold
            local_mix = (mix - 0.5) * 2.0

            polys["color"][mask_b, 0] = 1.0 - local_mix
            polys["color"][mask_b, 1] = 1.0
            polys["color"][mask_b, 2] = 1.0

        if np.any(mask_c):
            polys["color"][mask_c, 0] = 0.0
            polys["color"][mask_c, 1] = 1.0
            polys["color"][mask_c, 2] = 1.0
