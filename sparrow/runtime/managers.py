from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import moderngl
import moderngl_window as mglw
from moderngl_window.conf import settings
from moderngl_window.timers.base import BaseTimer

from sparrow.input.events import KeyEvent, MouseClickEvent, MouseMoveEvent
from sparrow.runtime.perf_timer import PerfCounterTimer


class InterfaceManager:
    """Manages the ModernGL context, window lifecycle, and input collection.

    This manager initializes the rendering surface and provides an abstraction
    for window-level operations. It is responsible for harvesting hardware
    events and maintaining the integrity of the OpenGL state.

    Attributes:
        window_config (mglw.WindowConfig): The configuration class for the window.
        wnd (mglw.widgets.Window): The actual window instance created by moderngl-window.
        ctx (moderngl.Context): The active ModernGL context.
    """

    def __init__(
        self,
        title: str = "Sparrow Engine",
        size: tuple = (1280, 720),
        show_cursor: bool = True,
    ):
        """Initializes the window and ModernGL context.

        Args:
            title (str): The text displayed in the window title bar.
            size (tuple): The initial width and height of the window.
        """
        settings.WINDOW.update(
            {
                "class": "moderngl_window.context.glfw.Window",
                "title": "Sparrow Engine",
                "size": size,
                "gl_version": (4, 6),
                "resizable": True,
                "cursor": show_cursor,
                "vsync": False,
            }
        )

        self.wnd: mglw.BaseWindow = mglw.create_window_from_settings()
        if not show_cursor:
            self.wnd.mouse_exclusivity = True

        self.timer: BaseTimer = PerfCounterTimer()
        self.timer.start()

        self.ctx = self.wnd.ctx
        self._event_buffer: List[Any] = []

        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        """Hooks internal methods to window events for event harvesting."""
        self.wnd.key_event_func = self._on_key_event
        self.wnd.mouse_position_event_func = self._on_mouse_move
        self.wnd.mouse_drag_event_func = self._on_mouse_move
        self.wnd.mouse_press_event_func = self._on_mouse_press
        self.wnd.mouse_release_event_func = self._on_mouse_release

    def _on_key_event(self, key: Any, action: Any, modifiers: Any) -> None:
        """Internal callback for keyboard activity."""
        self._event_buffer.append(KeyEvent(key, action, modifiers))

    def _on_mouse_move(self, x: int, y: int, dx: int, dy: int) -> None:
        """Internal callback for mouse motion."""
        self._event_buffer.append(MouseMoveEvent(x, y, dx, dy))

    def _on_mouse_press(self, x: int, y: int, button: int) -> None:
        """Internal callback for mouse clicks."""
        self._event_buffer.append(MouseClickEvent(x, y, button, action=1))

    def _on_mouse_release(self, x: int, y: int, button: int) -> None:
        """Internal callback for mouse releases."""
        self._event_buffer.append(MouseClickEvent(x, y, button, action=0))

    def poll_events(self) -> List[Any]:
        """Harvests and returns all events since the last call.

        Returns:
            List[Any]: A list of raw event tuples to be processed by the Input System.
        """
        events = self._event_buffer.copy()
        self._event_buffer.clear()
        return events

    def should_close(self) -> bool:
        """Checks if the window has received a close signal.

        Returns:
            bool: True if the window is closing, False otherwise.
        """
        return self.wnd.is_closing

    def clear(self, color: tuple = (0.0, 0.0, 0.0, 1.0)) -> None:
        """Clears the current framebuffer.

        Args:
            color (tuple): RGBA normalized color values.
        """
        self.ctx.clear(*color)

    def swap_buffers(self) -> None:
        """Swaps the window buffers to display the rendered frame."""
        self.wnd.swap_buffers()
        self.timer.next_frame()


@dataclass
class ResourceEntry:
    """Internal wrapper for a cached resource.

    Attributes:
        data (Any): The actual GPU or CPU resource (e.g., moderngl.Texture).
        tags (Set[str]): A collection of Scene IDs or labels that 'own' this resource.
    """

    data: Any
    tags: Set[str]


class ResourceManager:
    """Handles loading, storing, and fetching of CPU and GPU owned resources.

    This manager interfaces with ModernGL to upload assets to the GPU and
    manages their lifecycle using a tagging system to allow for targeted
    cleanup when switching scenes.

    Attributes:
        ctx (moderngl.Context): The active ModernGL context for resource creation.
        cache (Dict[str, ResourceEntry]): A master dictionary of loaded resources.
    """

    def __init__(self, ctx: moderngl.Context):
        """Initializes the Resource Manager.

        Args:
            ctx (moderngl.Context): The ModernGL context provided by the
                Interface Manager.
        """
        self.ctx = ctx
        self.cache: Dict[str, ResourceEntry] = {}

    def load_texture(self, path: str, scene_id: str) -> moderngl.Texture:
        """Loads a texture into GPU memory and caches it.

        If the texture is already loaded, it simply adds the new scene_id
        to the resource's tags.

        Args:
            path (str): Filepath to the texture asset.
            scene_id (str): The ID of the scene requesting the resource.

        Returns:
            moderngl.Texture: The loaded ModernGL texture object.
        """
        if path in self.cache:
            self.cache[path].tags.add(scene_id)
            return self.cache[path].data

        texture = moderngl.Texture()
        # TODO: Replace with actual load texture call

        self.cache[path] = ResourceEntry(data=texture, tags={scene_id})
        return texture

    def get_resource(self, path: str) -> Optional[Any]:
        """Fetches a resource from the cache if it exists.

        Args:
            path (str): The lookup key (usually the file path).

        Returns:
            Optional[Any]: The cached resource data or None.
        """
        entry = self.cache.get(path)
        return entry.data if entry else None

    def unload_unused(self, scene_id: str) -> None:
        """Purges resources that are no longer referenced by any active scene.

        This method iterates through the cache, removes the provided scene_id
        from all resource tags, and releases GPU memory for resources that
        have no remaining tags.

        Args:
            scene_id (str): The ID of the scene being destroyed.
        """
        to_delete = []

        for path, entry in self.cache.items():
            if scene_id in entry.tags:
                entry.tags.remove(scene_id)

            # If no scene is using this resource anymore, mark for deletion
            if not entry.tags:
                if hasattr(entry.data, "release"):
                    entry.data.release()
                to_delete.append(path)

        for path in to_delete:
            del self.cache[path]

    def release_all(self) -> None:
        """Forcefully clears all cached resources and releases GPU memory."""
        for entry in self.cache.values():
            if hasattr(entry.data, "release"):
                entry.data.release()
        self.cache.clear()
