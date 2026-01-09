from game.spatial.generator import (
    generate_dungeon,
    TILE_WALL,
    TILE_GOLD,
    TILE_WATER,
    TILE_FLOOR,
    find_spawn_point,
)
import math
from typing import Optional

from game.constants import GRID_HEIGHT, GRID_WIDTH, TILE_SIZE
from game.entities.player import create_player
from sparrow.core.components import BoxCollider, Sprite, Transform
from sparrow.core.world import World
from sparrow.graphics.light import AmbientLight
from sparrow.graphics.renderer import Renderer
from sparrow.input.handler import InputHandler
from sparrow.net.client import Client
from sparrow.net.host import Host
from sparrow.spatial.collision import aabb_vs_aabb, get_world_bounds
from sparrow.spatial.grid import Grid
from sparrow.types import EntityId


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

        self.local_pid: Optional[EntityId] = None

    def enter(self):
        """Called when the scene starts."""
        self.world.create_entity(AmbientLight(color=(0.2, 0.2, 0.4)))

        if self.host:
            print("[GAME] Generating Dungeon...")
            self.grid = generate_dungeon(GRID_WIDTH, GRID_HEIGHT)
            self._spawn_map_visuals()

            gx, gy = find_spawn_point(self.grid)
            wx, wy = self.grid.grid_to_world(gx, gy)

            self.local_pid = create_player(self.world, wx, wy)
            print(f"[GAME] Host spawned at Grid({gx}, {gy})")
        elif self.client:
            print("[GAME] Waiting for Map Data...")

    def _spawn_map_visuals(self):
        for x in range(self.grid.width):
            for y in range(self.grid.height):
                tile_id = self.grid.get(x, y)

                wx, wy = self.grid.grid_to_world(x, y)

                if tile_id == TILE_FLOOR:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite("floor_1", color=(1.0, 1.0, 1.0, 1.0)),  # Grey
                    )

                elif tile_id == TILE_WALL:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite("wall_mid", color=(1.0, 1.0, 1.0, 1.0)),  # Grey
                        BoxCollider(width=TILE_SIZE, height=TILE_SIZE),
                    )

                elif tile_id == TILE_GOLD:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        Sprite("wall_gold", color=(1.0, 0.8, 0.0, 1.0)),  # Gold Tint
                        BoxCollider(width=TILE_SIZE, height=TILE_SIZE),
                    )

                elif tile_id == TILE_WATER:
                    self.world.create_entity(
                        Transform(x=wx, y=wy),
                        # Water might be transparent or have a different layer
                        Sprite("water", color=(0.0, 0.0, 1.0, 0.5), layer=0),
                        # No Collider? or Trigger Collider?
                    )

    def update(self, dt: float):
        """Game Logic."""
        if self.client:
            self.client.update(self.world)

            if self.local_pid is None and self.client.my_entity_id is not None:
                self.local_pid = self.client.my_entity_id

            inp = self.world.get_resource(InputHandler)
            ax = inp.get_axis("LEFT", "RIGHT")
            ay = inp.get_axis("DOWN", "UP")
            self.client.send_input(ax, ay, 0)

        if self.host:
            self.host.update()

            for addr, eid in self.host.clients.items():
                if eid == -1:  # Needs Spawn
                    cx, cy = self.grid.grid_to_world(GRID_WIDTH // 2, GRID_HEIGHT // 2)
                    new_eid = create_player(
                        self.world, cx + 40, cy + 40
                    )  # Offset slightly

                    self.host.assign_entity(addr, int(new_eid))

            # Move Host (Local Input)
            if self.local_pid:
                inp = self.world.get_resource(InputHandler)
                self._move_entity(
                    self.local_pid,
                    inp.get_axis("LEFT", "RIGHT"),
                    inp.get_axis("DOWN", "UP"),
                    dt,
                )

            # Move Clients (Network Input)
            for addr, eid in self.host.clients.items():
                if eid != -1:
                    ax, ay, _ = self.host.get_input(addr)
                    self._move_entity(EntityId(eid), ax, ay, dt)

            # (In a real game, iterate all dynamic entities. For now, just players)
            if self.local_pid:
                t = self.world.component(self.local_pid, Transform)
                self.host.broadcast_state(self.local_pid, t.x, t.y)

            for _, eid in self.host.clients.items():
                if eid != -1:
                    t = self.world.component(EntityId(eid), Transform)
                    if t:
                        self.host.broadcast_state(eid, t.x, t.y)

        if self.local_pid:
            t = self.world.component(self.local_pid, Transform)
            if t:
                self.renderer.camera.look_at(t.x, t.y)
                self.renderer.camera.update(dt)

        if self.host:
            for addr, eid in self.host.clients.items():
                if eid == -1:  # Needs Spawn
                    print(f"[GAME] Initializing Client {addr}")

                    # 1. Send Map
                    self.host.send_map(addr, self.grid)

                    # 2. Find Safe Spawn
                    gx, gy = find_spawn_point(self.grid)
                    wx, wy = self.grid.grid_to_world(gx, gy)

                    # 3. Create Entity
                    new_eid = create_player(self.world, wx, wy)

                    # Tint Blue to distinguish
                    self.world.mutate_component(
                        new_eid,
                        Sprite("wizard_robe", color=(0.5, 0.5, 1.0, 1.0), layer=2),
                    )

                    # 4. Assign & Welcome
                    self.host.assign_entity(addr, int(new_eid))

    def _move_entity(
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
