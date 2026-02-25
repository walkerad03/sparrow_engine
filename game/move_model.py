from sparrow.core import Transform, Velocity
from sparrow.ecs import World
from sparrow.input.resources import InputState


def move_model_system(world: World) -> None:
    input_state = world.res_get(InputState)
    if not input_state:
        return

    view = world.query(Transform, Velocity)
    if len(view) == 0:
        return

    velocity = 0.0

    if input_state.is_action_pressed("move_forward"):
        velocity += 1.0

    if input_state.is_action_pressed("move_backward"):
        velocity -= 1.0

    ds_temp = view.Velocity.ds
    ds_temp[:, 1] = velocity
    view.Velocity.ds = ds_temp
