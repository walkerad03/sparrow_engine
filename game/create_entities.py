from sparrow.core import Transform, Velocity
from sparrow.ecs import World


def create_entities_system(world: World) -> None:
    for i in range(100000):
        ent = world.entity_add()
        world.comp_add(ent, Transform(x=i * 10.0, y=0.0))
        world.comp_add(ent, Velocity(dx=1.0))
