import logging

import pybullet as p

from sparrow.types import Vector3

logger = logging.getLogger("sparrow.physics")


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
