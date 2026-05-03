import json
import logging
import os

from sparrow.input.resources import InputMap

logger = logging.getLogger("sparrow.input")


def load_input_bindings(filepath: str) -> InputMap:
    """Loads key bindings from a JSON file into an InputMap resource."""
    input_map = InputMap()

    full_path = os.path.abspath(filepath)
    logger.info(f"Attempting to load input bindings from: {full_path}")

    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        for key_code_str, action_name in data.items():
            if key_code_str.startswith("m"):
                # Mouse button: "m0", "m1", etc.
                button_code = int(key_code_str[1:])
                input_map.bind_mouse(button_code, action_name)
            else:
                # Key code: "65", "69", etc.
                input_map.bind_key(int(key_code_str), action_name)

    except FileNotFoundError:
        logger.warning(
            f"Input configuration not found at {filepath}. Using defaults."
        )
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse input configuration: {e}")

    return input_map
