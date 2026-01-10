import random
from dataclasses import replace

from game.components.smooth_follow import SmoothFollow
from sparrow.core.components import Transform
from sparrow.core.world import World


def smooth_follow_system(world: World, dt: float) -> None:
    """
    Lerps entities towards their target position.
    """
    for eid, trans, follow in world.join(Transform, SmoothFollow):
        assert isinstance(trans, Transform) and isinstance(follow, SmoothFollow)

        target_trans = world.component(follow.target, Transform)
        if not target_trans:
            continue

        new_timer = follow._timer + dt
        current_wander_x, current_wander_y, current_wander_z = follow._current_wander

        next_wander_x = current_wander_x
        next_wander_y = current_wander_y
        next_wander_z = current_wander_z

        if follow.wander_radius > 0 and new_timer >= follow.wander_interval:
            new_timer = 0
            next_wander_x = random.uniform(-follow.wander_radius, follow.wander_radius)
            next_wander_y = random.uniform(-follow.wander_radius, follow.wander_radius)
            next_wander_z = random.uniform(-follow.wander_radius, follow.wander_radius)

        new_smooth_follow = replace(
            follow,
            _timer=new_timer,
            _current_wander=(next_wander_x, next_wander_y, next_wander_z),
        )
        world.mutate_component(eid, new_smooth_follow)

        target_x = target_trans.x + follow.offset_x + current_wander_x
        target_y = target_trans.y + follow.offset_y + current_wander_y
        target_z = target_trans.z + follow.offset_z + current_wander_z

        dx = target_x - trans.x
        dy = target_y - trans.y
        dz = target_z - trans.z

        lerp_factor = follow.speed * dt

        new_x = trans.x + dx * lerp_factor
        new_y = trans.y + dy * lerp_factor
        new_z = trans.z + dz * lerp_factor

        new_trans = replace(trans, x=new_x, y=new_y, z=new_z)
        world.mutate_component(eid, new_trans)
