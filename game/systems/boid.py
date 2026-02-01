import numpy as np

from game.components.boid import Boid
from game.components.player import Player
from sparrow.core.components import Transform, Velocity
from sparrow.core.query import Query
from sparrow.core.world import World
from sparrow.resources.core import SimulationTime
from sparrow.resources.rendering import RenderViewport
from sparrow.types import Quaternion


def boid_system(world: World) -> None:
    sim_time = world.try_resource(SimulationTime)
    viewport = world.try_resource(RenderViewport)
    if not (sim_time and viewport):
        return
    dt = sim_time.delta_seconds

    width, height = viewport.width, viewport.height

    for count, (transforms, player) in Query(world, Transform, Player):
        target_pos = np.array(
            [transforms.pos.x[0], transforms.pos.y[0]],
            dtype=np.float64,
        )
        break

    for count, (transforms, vels, boids) in Query(
        world, Transform, Velocity, Boid
    ):
        if count < 2:
            continue

        pos = transforms.pos.vec[:, :2]
        vel = vels.vec[:, :2]

        # Distance matrix computation
        diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        dist_sq = np.sum(diff**2, axis=2)

        np.fill_diagonal(dist_sq, np.inf)

        # Mask setups
        vis_range_sq = boids.visual_range[0] ** 2
        prot_range_sq = boids.protected_range[0] ** 2
        is_neighbor = dist_sq < vis_range_sq
        is_too_close = dist_sq < prot_range_sq

        # Flocking rules
        sep_forces = np.sum(diff * is_too_close[:, :, np.newaxis], axis=1)

        neighbor_counts = np.sum(is_neighbor, axis=1)[:, np.newaxis]
        neighbor_counts[neighbor_counts == 0] = 1.0

        avg_vel = (
            np.sum(
                vel[np.newaxis, :, :] * is_neighbor[:, :, np.newaxis], axis=1
            )
            / neighbor_counts
        )

        align_forces = avg_vel - vel

        avg_pos = (
            np.sum(
                pos[np.newaxis, :, :] * is_neighbor[:, :, np.newaxis], axis=1
            )
            / neighbor_counts
        )

        cohesion_forces = avg_pos - pos

        target_vec = target_pos - pos

        target_dist = np.linalg.norm(target_vec, axis=1, keepdims=True)
        target_dist[target_dist == 0] = 1.0

        desired_vel = (target_vec / target_dist) * 300.0
        seek_forces = desired_vel - vel

        margin = 50.0
        turn_strength = 500.0

        bound_forces = np.zeros_like(pos)

        bound_forces[:, 0] += (pos[:, 0] < margin) * turn_strength
        bound_forces[:, 0] -= (pos[:, 0] > (width - margin)) * turn_strength
        bound_forces[:, 1] += (pos[:, 1] < margin) * turn_strength
        bound_forces[:, 1] -= (pos[:, 1] > (height - margin)) * turn_strength

        # Integrate forces
        w_sep = boids.separation_weight[0]
        w_aln = boids.alignment_weight[0]
        w_coh = boids.cohesion_weight[0]
        w_tgt = boids.target_weight[0]

        total_force = (
            (sep_forces * w_sep)
            + (align_forces * w_aln)
            + (cohesion_forces * w_coh)
            + (seek_forces * w_tgt)
            + bound_forces
        )

        # Apply weights
        steer_factor = 5.0 * dt
        vels.vec[:, :2] += total_force * steer_factor

        speeds = np.linalg.norm(vels.vec[:, :2], axis=1, keepdims=True)
        max_speed = 600.0
        min_speed = 600.0

        too_fast = speeds > max_speed
        too_slow = (speeds < min_speed) & (speeds > 0)

        vels.vec[:, :2] = np.where(
            too_fast, vels.vec[:, :2] / speeds * max_speed, vels.vec[:, :2]
        )
        vels.vec[:, :2] = np.where(
            too_slow, vels.vec[:, :2] / speeds * min_speed, vels.vec[:, :2]
        )

        angles = np.arctan2(vels.vec[:, 1], vels.vec[:, 0]) - (np.pi / 2)

        for i in range(count):
            transforms.rot[i] = Quaternion.from_euler(0, angles[i], 0)
