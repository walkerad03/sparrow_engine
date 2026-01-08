from sparrow.types import Address
from typing import Dict
from sparrow.net.host import Host
from typing import Optional
import math

from sparrow.core.components import BoxCollider, Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.light import AmbientLight
from sparrow.graphics.renderer import Renderer
from sparrow.input.handler import InputHandler
from sparrow.spatial.collision import aabb_vs_aabb, get_world_bounds
from sparrow.spatial.grid import Grid
from sparrow.types import EntityId

from ..constants import GRID_HEIGHT, GRID_WIDTH, TILE_SIZE
from ..entities.player import create_player


class DungeonScene:
    def __init__(self, world: World, renderer: Renderer, host: Optional[Host] = None):
        self.world = world
        self.renderer = renderer
        self.host = host

        self.grid = Grid(GRID_WIDTH, GRID_HEIGHT, TILE_SIZE)

        self.local_player_id: EntityId

        self.network_players: Dict[Address, EntityId] = {}

    def enter(self):
        """Called when the scene starts."""
        # 1. Setup Environment
        self.world.create_entity(AmbientLight(color=(0.2, 0.2, 0.4)))

        # 2. Generate box level
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                # Draw borders
                if x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1:
                    self.grid.set(x, y, 1)

                    # Visual representation of the wall
                    wx, wy = self.grid.grid_to_world(x, y)
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite(texture_id="wall", color=(0.4, 0.4, 0.5, 1.0)),
                        BoxCollider(width=TILE_SIZE, height=TILE_SIZE),
                    )

        # 3. Spawn Player
        # Start in middle of room
        cx, cy = self.grid.grid_to_world(GRID_WIDTH // 2, GRID_HEIGHT // 2)
        self.local_player_id = create_player(self.world, cx, cy)

    def update(self, dt: float):
        """Game Logic (Movement, Spells, Physics)."""
        inp = self.world.get_resource(InputHandler)
        self._update_entity_from_input(
            self.local_player_id,
            inp.get_axis("LEFT", "RIGHT"),
            inp.get_axis("DOWN", "UP"),
            dt,
        )

        if self.host:
            for addr in self.host.clients:
                if addr not in self.network_players:
                    print(f"[GAME] Spawning new player for {addr}")
                    cx, cy = self.grid.grid_to_world(GRID_WIDTH // 2, GRID_HEIGHT // 2)
                    new_eid = create_player(self.world, cx + 20, cy + 20)
                    self.network_players[addr] = new_eid

            for addr, eid in self.network_players.items():
                input_data = self.host.get_input_for(addr)
                self._update_entity_from_input(eid, input_data[0], input_data[1], dt)

        if self.local_player_id:
            trans = self.world.component(self.local_player_id, Transform)
            if trans:
                self.renderer.camera.look_at(trans.x, trans.y)
                self.renderer.camera.update(dt)

    def _update_entity_from_input(
        self,
        eid: EntityId,
        dx: float,
        dy: float,
        dt: float,
    ) -> None:
        """Shared movement logic for Local and Network entities."""
        if not eid:
            return

        if dx != 0 or dy != 0:
            length = math.sqrt(dx * dx + dy * dy)
            dx /= length
            dy /= length

        trans = self.world.component(eid, Transform)
        collider = self.world.component(eid, BoxCollider)

        if not trans or not collider:
            return

        speed = 400.0

        next_x = trans.x + (dx * speed * dt)
        if not self._check_collision(next_x, trans.y, collider):
            trans = Transform(x=next_x, y=trans.y, scale=trans.scale)

        next_y = trans.y + (dy * speed * dt)
        if not self._check_collision(trans.x, next_y, collider):
            trans = Transform(x=trans.x, y=next_y, scale=trans.scale)

        self.world.mutate_component(eid, trans)

    def _check_collision(
        self, new_x: float, new_y: float, collider: BoxCollider
    ) -> bool:
        """Returns True if the proposed position hits a wall."""
        # Create a temporary Transform for the check
        temp_trans = Transform(x=new_x, y=new_y)

        # Get the world bounds of the player at the new position
        player_rect = get_world_bounds(temp_trans, collider)

        # Optimization: Only check the tiles immediately surrounding the player
        # Convert player rect to grid coordinates
        px, py, pw, ph = player_rect

        start_x, start_y = self.grid.world_to_grid(px, py)
        end_x, end_y = self.grid.world_to_grid(px + pw, py + ph)

        # Expand range by 1 to be safe
        for gx in range(start_x - 1, end_x + 2):
            for gy in range(start_y - 1, end_y + 2):
                if self.grid.get(gx, gy) == 1:  # Is Wall?
                    # Create a rect for this wall tile
                    wx, wy = self.grid.grid_to_world(gx, gy)
                    wall_rect = (
                        wx - TILE_SIZE / 2,
                        wy - TILE_SIZE / 2,
                        TILE_SIZE,
                        TILE_SIZE,
                    )

                    if aabb_vs_aabb(player_rect, wall_rect):
                        return True
        return False

    def render(self):
        """Draw the world."""
        self.renderer.render(self.world)
