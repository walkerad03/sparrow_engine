import logging
from dataclasses import dataclass
from typing import Optional

import pybullet as p

from sparrow.types import Vector3

logger = logging.getLogger("sparrow.physics")


@dataclass
class RaycastHit:
    """Engine-agnostic representation of a physics raycast result."""

    body_id: int
    hit_pos: Vector3
    hit_normal: Vector3


class PhysicsServer:
    def __init__(self, gravity: Vector3 = Vector3(0.0, -9.81, 0.0)):
        self.client_id = p.connect(p.DIRECT)
        if self.client_id < 0:
            logger.error("Failed to connect to PyBullet")
            return

        p.setGravity(*gravity, physicsClientId=self.client_id)

    def set_timestep(self, dt: float) -> None:
        p.setTimeStep(dt, physicsClientId=self.client_id)

    def step(self) -> None:
        p.stepSimulation(physicsClientId=self.client_id)

    def shutdown(self) -> None:
        if self.client_id >= 0:
            p.disconnect(physicsClientId=self.client_id)

    def raycast(self, start: Vector3, end: Vector3) -> Optional[RaycastHit]:
        """Projects a ray into the physics world and returns the first hit."""
        start_pt = (start.x, start.y, start.z)
        end_pt = (end.x, end.y, end.z)

        hit_info = p.rayTest(start_pt, end_pt, physicsClientId=self.client_id)[
            0
        ]
        hit_id = hit_info[0]

        if hit_id != -1:
            return RaycastHit(
                body_id=hit_id,
                hit_pos=Vector3(*hit_info[3]),
                hit_normal=Vector3(*hit_info[4]),
            )
        return None

    def get_mass(self, body_id: int) -> float:
        """Retrieves the mass of a physics body."""
        dynamics = p.getDynamicsInfo(
            body_id, -1, physicsClientId=self.client_id
        )
        return float(dynamics[0])

    def create_world_tether(
        self,
        body_id: int,
        hit_pos: Vector3,
        max_force: float = 100.0,  # Lowered default for more stretch
        erp: float = 0.05,  # Lowered default for a "lazy" correction
    ) -> int:
        """Creates a point-to-point constraint between a body and world space."""
        hit_pt = (hit_pos.x, hit_pos.y, hit_pos.z)

        pos, rot = p.getBasePositionAndOrientation(
            body_id, physicsClientId=self.client_id
        )
        inv_pos, inv_rot = p.invertTransform(pos, rot)
        local_hit_pos, _ = p.multiplyTransforms(
            inv_pos, inv_rot, hit_pt, (0, 0, 0, 1)
        )

        constraint_id = p.createConstraint(
            parentBodyUniqueId=body_id,
            parentLinkIndex=-1,
            childBodyUniqueId=-1,
            childLinkIndex=-1,
            jointType=p.JOINT_POINT2POINT,
            jointAxis=[0, 0, 0],
            parentFramePosition=local_hit_pos,
            childFramePosition=hit_pt,
            physicsClientId=self.client_id,
        )

        # Apply the stretch configurations
        p.changeConstraint(
            constraint_id,
            maxForce=max_force,
            erp=erp,
            physicsClientId=self.client_id,
        )
        return constraint_id

    def update_world_tether(
        self, constraint_id: int, target_pos: Vector3
    ) -> None:
        """Moves the world-space pivot point of an existing tether."""
        p.changeConstraint(
            constraint_id,
            jointChildPivot=(target_pos.x, target_pos.y, target_pos.z),
            physicsClientId=self.client_id,
        )

    def remove_tether(self, constraint_id: int) -> None:
        """Destroys an existing constraint."""
        p.removeConstraint(constraint_id, physicsClientId=self.client_id)
