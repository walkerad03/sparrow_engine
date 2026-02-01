from typing import List, Optional, Set

import pygame

from sparrow.input.context import InputContext
from sparrow.types import InputAction, Vector2


class InputHandler:
    def __init__(self):
        self._context_stack: List[InputContext] = []
        self._active_actions: Set[InputAction] = set()

        self._mouse_delta = [0.0, 0.0]
        self.mouse_sensitivity = 0.1
        self.mouse_visible = True

    def set_mouse_lock(self, locked: bool):
        """Helper to lock/hide the mouse for FPS controls."""
        self.mouse_visible = not locked
        pygame.mouse.set_visible(self.mouse_visible)
        pygame.event.set_grab(locked)
        if locked:
            # Center the mouse so we don't get a huge delta on first frame
            surf = pygame.display.get_surface()
            if surf:
                pygame.mouse.set_pos(surf.get_rect().center)

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

        elif event.type == pygame.MOUSEMOTION:
            # We add to the delta because multiple motion events
            # can happen between frames
            self._mouse_delta[0] += event.rel[0]
            self._mouse_delta[1] += event.rel[1]

    def get_mouse_delta(self) -> tuple[float, float]:
        """
        Returns the (dx, dy) since the last frame and resets the delta.
        Call this once per update loop.
        """
        dx = self._mouse_delta[0] * self.mouse_sensitivity
        dy = self._mouse_delta[1] * self.mouse_sensitivity

        # Reset delta for the next frame
        self._mouse_delta = [0.0, 0.0]

        return dx, dy

    def get_mouse_position(self) -> Vector2:
        """
        Return screen space mouse position in a range of 0-1.
        """
        pos = pygame.mouse.get_pos()
        surface = pygame.display.get_surface()
        if surface is None:
            return Vector2(0.0, 0.0)

        w, h = surface.get_size()
        return Vector2(pos[0] / w, 1.0 - (pos[1] / h))

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
