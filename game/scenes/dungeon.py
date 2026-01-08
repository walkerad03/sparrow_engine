import math
from typing import Dict, Optional

from sparrow.core.components import BoxCollider, Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.light import AmbientLight
from sparrow.graphics.renderer import Renderer
from sparrow.input.handler import InputHandler
from sparrow.net.client import Client
from sparrow.net.host import Host
from sparrow.spatial.collision import aabb_vs_aabb, get_world_bounds
from sparrow.spatial.grid import Grid
from sparrow.types import Address, EntityId

from game.constants import GRID_HEIGHT, GRID_WIDTH, TILE_SIZE
from game.entities.player import create_player


class DungeonScene:
    def __init__(
        self,
        world: World,
        renderer: Renderer,
        host: Optional[Host] = None,
        client: Optional[Client] = None,
    ):
        self.world = world
        self.renderer = renderer
        self.host = host
        self.client = client
        self.grid = Grid(GRID_WIDTH, GRID_HEIGHT, TILE_SIZE)

        self.local_player_id: Optional[EntityId] = None

        self.network_players: Dict[Address, EntityId] = {}

    def _build_level(self) -> None:
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                # Draw borders
                if x == 0 or x == GRID_WIDTH - 1 or y == 0 or y == GRID_HEIGHT - 1:
                    self.grid.set(x, y, 1)

                    wx, wy = self.grid.grid_to_world(x, y)
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite(texture_id="wall", color=(0.4, 0.4, 0.5, 1.0)),
                        BoxCollider(width=TILE_SIZE, height=TILE_SIZE),
                    )

    def enter(self):
        """Called when the scene starts."""
        self.world.create_entity(AmbientLight(color=(0.2, 0.2, 0.4)))
        self._build_level()

        cx, cy = self.grid.grid_to_world(GRID_WIDTH // 2, GRID_HEIGHT // 2)

        if self.host:
            self.local_player_id = create_player(self.world, cx, cy)
        elif self.client:
            pass  # Wait for welcome

        else:
            self.local_player_id = create_player(self.world, cx, cy)

    def update(self, dt: float):
        """Game Logic."""
        if self.client and self.local_player_id is None:
            if self.client.my_entity_id is not None:
                self.local_player_id = self.client.my_entity_id

                if self.world.has(self.local_player_id, Sprite):
                    current_sprite = self.world.component(self.local_player_id, Sprite)
                    self.world.mutate_component(
                        self.local_player_id,
                        Sprite(
                            texture_id=current_sprite.texture_id,
                            color=(1.0, 0.2, 0.2, 1.0),  # RED
                            layer=current_sprite.layer,
                        ),
                    )

        if self.host:
            for addr in self.host.clients:
                if addr not in self.network_players:
                    print(f"[GAME] Spawning new player for {addr}")

                    cx, cy = self.grid.grid_to_world(GRID_WIDTH // 2, GRID_HEIGHT // 2)
                    new_eid = create_player(self.world, cx + 20, cy + 20)
                    self.network_players[addr] = new_eid

                    self.world.mutate_component(
                        new_eid,
                        Sprite(
                            texture_id="wizard_robe",
                            color=(0.5, 0.5, 1.0, 1.0),  # BLUE
                            layer=2,
                        ),
                    )

                    self.host.send_welcome(addr, int(new_eid))

        if self.local_player_id:
            inp = self.world.get_resource(InputHandler)
            self._update_entity_from_input(
                self.local_player_id,
                inp.get_axis("LEFT", "RIGHT"),
                inp.get_axis("DOWN", "UP"),
                dt,
            )

        if self.host:
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
