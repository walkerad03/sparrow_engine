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
            is_kinematic = bool(view.RigidBody.is_kinematic[i])

            extents = tuple(view.Collider.extents[i])
            shape_id = p.createCollisionShape(
                p.GEOM_BOX,
                halfExtents=extents,
                physicsClientId=physics.client_id,
            )

            new_body_id = p.createMultiBody(
                baseMass=0.0 if is_kinematic else mass,
                baseCollisionShapeIndex=shape_id,
                basePosition=pos,
                baseOrientation=rot,
                physicsClientId=physics.client_id,
            )

            if is_kinematic:
                p.changeDynamics(
                    new_body_id,
                    -1,
                    activationState=p.ACTIVATION_STATE_DISABLE_SLEEPING,
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
        # Before stepping, sync Kinematic bodies FROM ECS TO Bullet
        view = world.query(Transform, RigidBody)
        for i in range(len(view)):
            if (
                view.RigidBody.is_kinematic[i]
                and view.RigidBody.body_id[i] != -1
            ):
                p.resetBasePositionAndOrientation(
                    view.RigidBody.body_id[i],
                    tuple(view.Transform.pos[i]),
                    tuple(view.Transform.rot[i]),
                    physicsClientId=physics.client_id,
                )

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
    is_kinematic = view.RigidBody.is_kinematic
    positions = view.Transform.pos.copy()
    rotations = view.Transform.rot.copy()

    modified = False
    for i in range(len(view)):
        body_id = body_ids[i]
        if body_id == -1 or is_kinematic[i]:
            continue

        pos, rot = p.getBasePositionAndOrientation(
            body_id, physicsClientId=physics.client_id
        )

        positions[i] = pos
        rotations[i] = rot
        modified = True

    # Explicitly write back to the ECS proxies
    if modified:
        view.Transform.pos = positions
        view.Transform.rot = rotations
