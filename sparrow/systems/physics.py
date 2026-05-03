import pybullet as p

from sparrow.core.components import Transform
from sparrow.core.time import SimulationTime
from sparrow.ecs.world import World
from sparrow.physics.components import Collider, RigidBody
from sparrow.physics.server import PhysicsServer


def physics_init_system(world: World) -> None:
    physics = world.res_get(PhysicsServer)
    if not physics:
        return

    view = world.query(Transform, RigidBody, Collider)
    if len(view) == 0:
        return

    # We must operate on a copy and then SET it back to the proxy
    # to ensure the ECS storage is updated.
    body_ids = view.RigidBody.body_id.copy()

    modified = False
    for i in range(len(view)):
        if body_ids[i] == -1:
            pos = tuple(view.Transform.pos[i])
            rot = tuple(view.Transform.rot[i])
            mass = float(view.RigidBody.mass[i])

            extents = tuple(view.Collider.extents[i])
            shape_id = p.createCollisionShape(
                p.GEOM_BOX,
                halfExtents=extents,
                physicsClientId=physics.client_id,
            )

            new_body_id = p.createMultiBody(
                baseMass=mass,
                baseCollisionShapeIndex=shape_id,
                basePosition=pos,
                baseOrientation=rot,
                physicsClientId=physics.client_id,
            )

            body_ids[i] = new_body_id
            modified = True

    if modified:
        view.RigidBody.body_id = body_ids


def physics_step_system(world: World) -> None:
    """Advances the PyBullet simulation."""
    physics = world.res_get(PhysicsServer)
    sim_time = world.res_get(SimulationTime)

    if physics and sim_time:
        physics.set_timestep(sim_time.fixed_dt)
        physics.step()


def physics_sync_system(world: World) -> None:
    """Synchronizes PyBullet transforms back to the ECS Transform components."""
    physics = world.res_get(PhysicsServer)
    if not physics:
        return

    view = world.query(Transform, RigidBody)
    if len(view) == 0:
        return

    # Get local copies of the entire arrays
    body_ids = view.RigidBody.body_id
    positions = view.Transform.pos.copy()
    rotations = view.Transform.rot.copy()

    for i in range(len(view)):
        body_id = body_ids[i]
        if body_id == -1:
            continue

        pos, rot = p.getBasePositionAndOrientation(
            body_id, physicsClientId=physics.client_id
        )

        positions[i] = pos
        rotations[i] = rot

    # Explicitly write back to the ECS proxies
    view.Transform.pos = positions
    view.Transform.rot = rotations
