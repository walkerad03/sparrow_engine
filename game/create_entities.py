import math
import random

from game.asteroid_orbit import AsteroidOrbit
from game.gravity import GravityObject, circular_orbit_speed
from sparrow.assets import AssetServer
from sparrow.core import Transform, Velocity
from sparrow.ecs import World
from sparrow.graphics.integration import Camera, Material, Mesh
from sparrow.types import Vector3

ASTEROID_MODEL_PATH = "../../game/models/asteroid1.obj"
PLANET_MODEL_PATH = "../../game/models/planet.obj"
WATER_MODEL_PATH = "../../game/models/planet_water.obj"
PLANET_COLOR = (0.428, 0.721, 0.427, 1.0)
WATER_COLOR = (0.275, 0.646, 0.906, 1.0)
BELT_BROWN_MIN = (0.30, 0.20, 0.12)
BELT_BROWN_MAX = (0.55, 0.38, 0.24)
BELT_COUNT = 40000
ASTEROID_SPIN_RATE = 1.0


def _spawn_gravity_body(
    world: World,
    mesh_handle,
    *,
    pos: Vector3,
    scale: float,
    color: tuple[float, float, float, float],
    emission: float,
    roughness: float,
    metallic: float,
    mass: float,
    velocity: Vector3 = Vector3(0.0, 0.0, 0.0),
    is_static: bool = False,
) -> int:
    eid = world.entity_add()
    world.comp_add(
        eid,
        Transform(
            pos=pos,
            scale=Vector3(x=scale, y=scale, z=scale),
        ),
        Velocity(ds=velocity),
        Mesh(handle=mesh_handle),
        Material(
            base_color=color,
            emissive=emission,
            roughness=roughness,
            metallic=metallic,
        ),
        GravityObject(mass=mass, is_static=is_static),
    )
    return eid


def _spawn_belt_asteroid(
    world: World,
    mesh_handle,
    *,
    radius: float,
    phase: float,
    angular_velocity: float,
    spin_phase: float,
    color: tuple[float, float, float, float],
    scale: float,
) -> int:
    px = radius * math.cos(phase)
    pz = radius * math.sin(phase)
    vx = -radius * angular_velocity * math.sin(phase)
    vz = radius * angular_velocity * math.cos(phase)

    eid = world.entity_add()
    world.comp_add(
        eid,
        Transform(
            pos=Vector3(px, 0.0, pz),
            scale=Vector3(x=scale, y=scale, z=scale),
        ),
        Velocity(ds=Vector3(vx, 0.0, vz)),
        Mesh(handle=mesh_handle),
        Material(base_color=color, emissive=0.0),
        AsteroidOrbit(
            radius=radius,
            angular_velocity=angular_velocity,
            phase=phase,
            spin_angular_velocity=ASTEROID_SPIN_RATE,
            spin_phase=spin_phase,
            center=Vector3(0.0, 0.0, 0.0),
            enabled=True,
        ),
    )
    return eid


def create_entities_system(world: World) -> None:
    asset_server = world.res_get(AssetServer)
    if not asset_server:
        return

    planet_mesh = asset_server.load(path=PLANET_MODEL_PATH)
    water_mesh = asset_server.load(path=WATER_MODEL_PATH)
    asteroid = asset_server.load(ASTEROID_MODEL_PATH)

    star_mass = 100.0
    _spawn_gravity_body(
        world,
        planet_mesh,
        pos=Vector3(0.0, 0.0, 0.0),
        scale=10.0,
        color=PLANET_COLOR,
        emission=0.0,
        roughness=1.0,
        metallic=0.0,
        mass=star_mass,
        is_static=True,
    )

    _spawn_gravity_body(
        world,
        water_mesh,
        pos=Vector3(0.0, 0.0, 0.0),
        scale=10.0,
        color=WATER_COLOR,
        emission=0.0,
        roughness=0.0,
        metallic=1.0,
        mass=0.0,
        is_static=True,
    )

    belt_inner = 11.13
    belt_outer = 30.72
    for _ in range(BELT_COUNT):
        radius = random.uniform(belt_inner, belt_outer)
        phase = random.uniform(0.0, math.tau)
        speed = circular_orbit_speed(radius, star_mass) * random.uniform(
            0.90, 1.10
        )
        angular_velocity = -(speed / radius) if radius > 0.0 else 0.0

        color = (
            random.uniform(BELT_BROWN_MIN[0], BELT_BROWN_MAX[0]),
            random.uniform(BELT_BROWN_MIN[1], BELT_BROWN_MAX[1]),
            random.uniform(BELT_BROWN_MIN[2], BELT_BROWN_MAX[2]),
            1.0,
        )

        _spawn_belt_asteroid(
            world,
            asteroid,
            radius=radius,
            phase=phase,
            angular_velocity=angular_velocity,
            spin_phase=random.uniform(0.0, math.tau),
            color=color,
            scale=random.uniform(0.01, 0.03),
        )

    cam = world.entity_add()
    world.comp_add(
        cam,
        Transform(pos=Vector3(0.0, 8.0, 60.0)),
        Camera(active=True),
    )
