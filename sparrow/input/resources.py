# sparrow/input/resources.py
from dataclasses import dataclass, field


@dataclass
class InputMap:
    """Resource: Maps raw hardware codes to semantic action names."""

    key_bindings: dict[int, str] = field(default_factory=dict)

    def bind_key(self, key_code: int, action_name: str) -> None:
        self.key_bindings[key_code] = action_name


@dataclass
class InputState:
    """Resource: Holds the current active state of semantic actions."""

    active_actions: dict[str, bool] = field(default_factory=dict)

    def is_action_pressed(self, action_name: str) -> bool:
        """Returns True if the action is currently held down."""
        return self.active_actions.get(action_name, False)
