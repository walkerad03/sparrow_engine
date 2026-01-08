from typing import Dict, Optional

from sparrow.types import InputAction


class InputContext:
    """
    A named collection of Key -> Action mappings.
    Example:
        gameplay = InputContext("gameplay", {K_w: "UP"})
        menu = InputContext("menu", {K_ESCAPE: "CLOSE_MENU"})
    """

    def __init__(self, name: str, bindings: Dict[int, InputAction] | None = None):
        self.name = name
        # Mapping: Pygame Key Code (int) -> Action String
        self.bindings: Dict[int, InputAction] = bindings if bindings else {}
        self.blocks_lower: bool = (
            False  # If True, no inputs pass to contexts below this one
        )

    def bind(self, key: int, action: InputAction):
        """Map a physical key to an abstract action."""
        self.bindings[key] = action

    def unbind(self, key: int):
        if key in self.bindings:
            del self.bindings[key]

    def get_action(self, key: int) -> Optional[InputAction]:
        return self.bindings.get(key)
