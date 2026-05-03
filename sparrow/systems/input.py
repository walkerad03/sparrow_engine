from sparrow.ecs.world import World
from sparrow.input.binding_loader import load_input_bindings
from sparrow.input.events import KeyEvent, MouseClickEvent
from sparrow.input.resources import InputMap, InputState


def input_system(world: World) -> None:
    input_map = world.res_get(InputMap)
    input_state = world.res_get(InputState)

    if not input_map:
        input_map = load_input_bindings("sparrow/config/key_bindings.json")
        world.res_add(input_map)

    if not input_state:
        input_state = InputState()
        world.res_add(input_state)

    key_events = world.event_get(KeyEvent)

    for event in key_events:
        action_name = input_map.key_bindings.get(event.key)

        if action_name:
            if event.action == 1:
                input_state.active_actions[action_name] = True
            elif event.action == 0:
                input_state.active_actions[action_name] = False

    mouse_events = world.event_get(MouseClickEvent)

    for event in mouse_events:
        action_name = input_map.mouse_bindings.get(event.button)

        if action_name:
            if event.action == 1:
                input_state.active_actions[action_name] = True
            elif event.action == 0:
                input_state.active_actions[action_name] = False
