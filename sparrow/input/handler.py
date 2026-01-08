from typing import List, Optional, Set

import pygame

from sparrow.input.context import InputContext
from sparrow.types import InputAction


class InputHandler:
    def __init__(self):
        self._context_stack: List[InputContext] = []
        self._active_actions: Set[InputAction] = set()

    def push_context(self, context: InputContext):
        """Add a context to the top of the stack (highest priority)."""
        self._context_stack.append(context)

    def pop_context(self, name: str) -> Optional[InputContext]:
        """Remove a context by name."""
        for i in range(len(self._context_stack) - 1, -1, -1):
            if self._context_stack[i].name == name:
                return self._context_stack.pop(i)
        return None

    def process_event(self, event: pygame.event.Event) -> None:
        """Feed Pygame events here to update state."""
        if event.type == pygame.KEYDOWN:
            action = self._resolve_key(event.key)
            if action:
                self._active_actions.add(action)

        elif event.type == pygame.KEYUP:
            # TODO: Handle desync if context changes while key is held.
            action = self._resolve_key(event.key)
            if action and action in self._active_actions:
                self._active_actions.remove(action)

    def is_pressed(self, action: InputAction) -> bool:
        """Returns True if the action button is currently held."""
        return action in self._active_actions

    def get_axis(self, negative: InputAction, positive: InputAction) -> float:
        """
        Returns -1.0, 0.0, or 1.0 based on two opposing actions.
        Useful for movement (LEFT, RIGHT).
        """
        val = 0.0
        if self.is_pressed(positive):
            val += 1.0
        if self.is_pressed(negative):
            val -= 1.0
        return val

    def _resolve_key(self, key_code: int) -> Optional[InputAction]:
        """Finds the action for a key by walking down the stack."""
        # Iterate backwards (Top -> Bottom)
        for context in reversed(self._context_stack):
            action = context.get_action(key_code)
            if action:
                return action

            # If this context is blocking (e.g., a modal menu), stop looking
            if context.blocks_lower:
                break
        return None
