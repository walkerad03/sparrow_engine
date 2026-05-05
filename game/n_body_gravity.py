from dataclasses import dataclass

import numpy as np
import pybullet as p

from sparrow.core import Transform
from sparrow.ecs import World
from sparrow.physics.components import RigidBody
from sparrow.physics.server import PhysicsServer


@dataclass
class GravityPointSource:
    """Tag component to denote that this body contributes to and is affected by custom gravity."""

    pass


def n_body_gravity_system(world: World) -> None:
    physics = world.res_get(PhysicsServer)
    if not physics:
        return

    view = world.query(Transform, RigidBody, GravityPointSource)
    if len(view) < 2:
        return

    mask = (
        (view.RigidBody.body_id != -1)
        & (~view.RigidBody.is_kinematic)
        & (view.RigidBody.mass > 0)
    )

    active_ids = view.RigidBody.body_id[mask]
    pos = view.Transform.pos[mask]  # Shape (N, 3)
    masses = view.RigidBody.mass[mask]  # Shape (N,)

    num_bodies = len(active_ids)
    if num_bodies < 2:
        return

    diffs = pos[np.newaxis, :, :] - pos[:, np.newaxis, :]  # Shape (N, N, 3)

    dist_sq = np.sum(diffs**2, axis=-1)  # Shape (N, N)

    softening = 0.1
    dist_sq += softening**2

    mass_matrix = masses[:, np.newaxis] * masses[np.newaxis, :]
    GAME_G = 10.0
    force_mag = (GAME_G * mass_matrix) / dist_sq  # Shape (N, N)

    inv_dist = 1.0 / np.sqrt(dist_sq)
    force_vectors = (
        diffs * (inv_dist * force_mag)[..., np.newaxis]
    )  # Shape (N, N, 3)

    total_forces = np.sum(force_vectors, axis=1)  # Shape (N, 3)

    for i in range(num_bodies):
        p.applyExternalForce(
            int(active_ids[i]),
            -1,
            forceObj=total_forces[i],
            posObj=pos[i],
            flags=p.WORLD_FRAME,
            physicsClientId=physics.client_id,
        )
