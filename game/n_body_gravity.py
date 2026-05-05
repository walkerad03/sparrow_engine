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
    """
    Applies an N-body gravitational attraction between all entities tagged
    with GravityPointSource.
    """
    physics = world.res_get(PhysicsServer)
    if not physics:
        return

    # Query for dynamic bodies with the GravityPointSource tag
    view = world.query(Transform, RigidBody, GravityPointSource)
    if len(view) < 2:
        return

    positions = view.Transform.pos
    masses = view.RigidBody.mass
    body_ids = view.RigidBody.body_id
    is_kinematic = view.RigidBody.is_kinematic

    # Filter for active dynamic (non-kinematic) bodies with mass
    indices = []
    for i in range(len(view)):
        if body_ids[i] != -1 and not is_kinematic[i] and masses[i] > 0:
            indices.append(i)

    if len(indices) < 2:
        return

    # F = G * (m1 * m2) / r^2
    GAME_G = 10.0

    for i in range(len(indices)):
        idx_a = indices[i]
        pos_a = positions[idx_a]
        m_a = masses[idx_a]
        id_a = body_ids[idx_a]

        total_force = np.zeros(3, dtype="f4")

        for j in range(len(indices)):
            if i == j:
                continue

            idx_b = indices[j]
            pos_b = positions[idx_b]
            m_b = masses[idx_b]

            # Vector from A to B
            diff = pos_b - pos_a
            dist_sq = np.dot(diff, diff)

            if dist_sq < 0.1:  # Softening
                continue

            dist = np.sqrt(dist_sq)
            force_mag = (GAME_G * m_a * m_b) / dist_sq
            force_vec = (diff / dist) * force_mag
            total_force += force_vec

        # Apply the cumulative force to the PyBullet body
        p.applyExternalForce(
            id_a,
            -1,
            forceObj=tuple(total_force),
            posObj=tuple(pos_a),
            flags=p.WORLD_FRAME,
            physicsClientId=physics.client_id,
        )
