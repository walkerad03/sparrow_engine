from dataclasses import dataclass

import numpy as np

from sparrow.core import Transform, Velocity
from sparrow.core.time import SimulationTime
from sparrow.ecs import World
from sparrow.types import Vector3


@dataclass
class AsteroidOrbit:
    radius: float = 1.0
    angular_velocity: float = -1.0
    phase: float = 0.0
    spin_angular_velocity: float = 0.25
    spin_phase: float = 0.0
    center: Vector3 = Vector3(0.0, 0.0, 0.0)
    enabled: bool = True


def asteroid_orbit_system(world: World) -> None:
    sim_time = world.res_get(SimulationTime)
    if not sim_time:
        return

    dt = sim_time.fixed_dt
    if dt <= 0.0:
        return

    view = world.query(Transform, Velocity, AsteroidOrbit)
    if len(view) == 0:
        return

    enabled = view.AsteroidOrbit.enabled
    if not enabled.any():
        return

    idx = np.flatnonzero(enabled)
    radius = view.AsteroidOrbit.radius[idx]
    omega = view.AsteroidOrbit.angular_velocity[idx]
    phase = view.AsteroidOrbit.phase[idx]
    spin_omega = view.AsteroidOrbit.spin_angular_velocity[idx]
    spin_phase = view.AsteroidOrbit.spin_phase[idx]
    center = view.AsteroidOrbit.center[idx]

    next_phase = phase + (omega * dt)
    next_spin_phase = spin_phase + (spin_omega * dt)

    cos_cur = np.cos(phase)
    sin_cur = np.sin(phase)
    cos_next = np.cos(next_phase)
    sin_next = np.sin(next_phase)

    pos_x = center[:, 0] + (radius * cos_cur)
    pos_z = center[:, 2] + (radius * sin_cur)
    next_x = center[:, 0] + (radius * cos_next)
    next_z = center[:, 2] + (radius * sin_next)

    inv_dt = 1.0 / dt
    vel_x = (next_x - pos_x) * inv_dt
    vel_z = (next_z - pos_z) * inv_dt

    positions = view.Transform.pos
    rotations = view.Transform.rot
    velocities = view.Velocity.ds
    phases = view.AsteroidOrbit.phase
    spin_phases = view.AsteroidOrbit.spin_phase

    positions[idx, 0] = pos_x
    positions[idx, 1] = center[:, 1]
    positions[idx, 2] = pos_z

    velocities[idx, 0] = vel_x
    velocities[idx, 1] = 0.0
    velocities[idx, 2] = vel_z

    half_spin = next_spin_phase * 0.5
    rotations[idx, 0] = 0.0
    rotations[idx, 1] = np.sin(half_spin)
    rotations[idx, 2] = 0.0
    rotations[idx, 3] = np.cos(half_spin)

    phases[idx] = next_phase
    spin_phases[idx] = next_spin_phase

    view.Transform.pos = positions
    view.Transform.rot = rotations
    view.Velocity.ds = velocities
    view.AsteroidOrbit.phase = phases
    view.AsteroidOrbit.spin_phase = spin_phases
