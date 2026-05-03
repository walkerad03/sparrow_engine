import logging
import math
import time
from dataclasses import dataclass

import numpy as np

from sparrow.core import Transform, Velocity
from sparrow.core.time import SimulationTime
from sparrow.ecs import World

logger = logging.getLogger("game.gravity")

GRAVITY_G = 0.1
SOFTENING = 0.5
MAX_ACCEL = 500.0
BH_THETA = 1.0
BH_LEAF_CAPACITY = 8
BH_MIN_HALF_SIZE = 0.01
# In Python, Barnes-Hut traversal has high per-node overhead.
# Keep direct NumPy solver for small/medium body counts.
BH_DIRECT_THRESHOLD = 3000
BH_DIRECT_MAX_BYTES = 512 * 1024 * 1024
BH_LOG_EVERY_N_STEPS = 30
BH_SLOW_STEP_WARN_MS = 50.0

_bh_step_counter = 0


@dataclass
class GravityObject:
    mass: float = 1.0
    is_static: bool = False
    enabled: bool = True


@dataclass(slots=True)
class _OctreeNode:
    center_x: float
    center_y: float
    center_z: float
    half_size: float
    mass: float
    com_x: float
    com_y: float
    com_z: float
    indices: np.ndarray | None
    children: list["_OctreeNode"] | None


@dataclass(slots=True)
class _TreeBuildStats:
    nodes: int = 0
    leaves: int = 0
    max_depth: int = 0


def circular_orbit_speed(radius: float, central_mass: float) -> float:
    if radius <= 0.0 or central_mass <= 0.0:
        return 0.0
    return math.sqrt((GRAVITY_G * central_mass) / radius)


def gravity_system(world: World) -> None:
    global _bh_step_counter
    step_start = time.perf_counter()

    sim_time = world.res_get(SimulationTime)
    if not sim_time:
        return

    dt = sim_time.fixed_dt
    if dt <= 0.0:
        return

    view = world.query(Transform, Velocity, GravityObject)
    count = len(view)
    if count < 2:
        return

    positions = view.Transform.pos
    velocities = view.Velocity.ds
    masses = view.GravityObject.mass
    static_flags = view.GravityObject.is_static
    enabled_flags = view.GravityObject.enabled

    active = enabled_flags & (masses > 0.0)
    active_idx = np.flatnonzero(active)
    if active_idx.size < 2:
        return

    pos = positions[active_idx]
    mass = masses[active_idx]
    mode = "direct"
    tree_stats = _TreeBuildStats()
    tree_build_ms = 0.0
    solve_ms = 0.0
    visited_nodes = 0

    solve_start = time.perf_counter()
    if _should_use_direct(active_idx.size):
        accel = _compute_direct_accel(pos, mass)
    else:
        mode = "barnes_hut"
        build_start = time.perf_counter()
        root, tree_stats = _build_root_octree(pos, mass)
        tree_build_ms = (time.perf_counter() - build_start) * 1000.0
        if root is None:
            return
        accel = np.zeros_like(pos, dtype=np.float64)
        for i in range(active_idx.size):
            a_i, visits_i = _accel_from_tree(root, i, pos, mass)
            accel[i] = a_i
            visited_nodes += visits_i
    solve_ms = (time.perf_counter() - solve_start) * 1000.0

    if MAX_ACCEL > 0.0:
        mag = np.linalg.norm(accel, axis=1)
        over = mag > MAX_ACCEL
        if over.any():
            accel[over] *= (MAX_ACCEL / mag[over])[:, np.newaxis]

    dynamic = ~static_flags[active_idx]
    if not dynamic.any():
        return

    dynamic_idx = active_idx[dynamic]
    velocities[dynamic_idx] += accel[dynamic] * dt
    view.Velocity.ds = velocities

    _bh_step_counter += 1
    total_ms = (time.perf_counter() - step_start) * 1000.0
    if total_ms >= BH_SLOW_STEP_WARN_MS:
        logger.warning(
            "gravity step slow: total=%.2fms mode=%s active=%d dynamic=%d "
            "build=%.2fms solve=%.2fms nodes=%d leaves=%d depth=%d visits=%d",
            total_ms,
            mode,
            int(active_idx.size),
            int(dynamic.sum()),
            tree_build_ms,
            solve_ms,
            tree_stats.nodes,
            tree_stats.leaves,
            tree_stats.max_depth,
            visited_nodes,
        )
    elif (_bh_step_counter % BH_LOG_EVERY_N_STEPS) == 0:
        logger.info(
            "gravity step: total=%.2fms mode=%s active=%d dynamic=%d "
            "build=%.2fms solve=%.2fms nodes=%d leaves=%d depth=%d visits=%d",
            total_ms,
            mode,
            int(active_idx.size),
            int(dynamic.sum()),
            tree_build_ms,
            solve_ms,
            tree_stats.nodes,
            tree_stats.leaves,
            tree_stats.max_depth,
            visited_nodes,
        )


def _compute_direct_accel(pos: np.ndarray, mass: np.ndarray) -> np.ndarray:
    delta = pos[np.newaxis, :, :] - pos[:, np.newaxis, :]
    dist_sq = np.einsum("ijk,ijk->ij", delta, delta) + (SOFTENING * SOFTENING)
    np.fill_diagonal(dist_sq, np.inf)

    inv_r = 1.0 / np.sqrt(dist_sq)
    inv_r3 = inv_r / dist_sq

    return GRAVITY_G * np.einsum("ijk,ij,j->ik", delta, inv_r3, mass)


def _should_use_direct(active_count: int) -> bool:
    if active_count > BH_DIRECT_THRESHOLD:
        return False

    # Direct solver allocates several O(N^2) arrays (delta, dist_sq, inv_r, inv_r3).
    est_bytes = 48 * active_count * active_count
    return est_bytes <= BH_DIRECT_MAX_BYTES


def _build_root_octree(
    pos: np.ndarray, mass: np.ndarray
) -> tuple[_OctreeNode | None, _TreeBuildStats]:
    stats = _TreeBuildStats()
    if pos.shape[0] == 0:
        return None, stats

    mins = pos.min(axis=0)
    maxs = pos.max(axis=0)
    center = ((mins + maxs) * 0.5).astype(np.float64, copy=False)
    span = float(np.max(maxs - mins))
    half_size = max(BH_MIN_HALF_SIZE, (span * 0.5) + 1e-4)
    cx = float(center[0])
    cy = float(center[1])
    cz = float(center[2])

    all_indices = np.arange(pos.shape[0], dtype=np.int64)
    root = _build_octree_node(
        pos,
        mass,
        all_indices,
        cx,
        cy,
        cz,
        half_size,
        depth=0,
        stats=stats,
    )
    return root, stats


def _build_octree_node(
    pos: np.ndarray,
    mass: np.ndarray,
    indices: np.ndarray,
    center_x: float,
    center_y: float,
    center_z: float,
    half_size: float,
    depth: int,
    stats: _TreeBuildStats,
) -> _OctreeNode:
    stats.nodes += 1
    if depth > stats.max_depth:
        stats.max_depth = depth

    node_mass = float(np.sum(mass[indices]))
    if node_mass <= 0.0:
        stats.leaves += 1
        return _OctreeNode(
            center_x=center_x,
            center_y=center_y,
            center_z=center_z,
            half_size=half_size,
            mass=0.0,
            com_x=center_x,
            com_y=center_y,
            com_z=center_z,
            indices=indices,
            children=None,
        )

    weighted_pos = pos[indices] * mass[indices][:, np.newaxis]
    node_com = np.sum(weighted_pos, axis=0) / node_mass
    com_x = float(node_com[0])
    com_y = float(node_com[1])
    com_z = float(node_com[2])

    if indices.size <= BH_LEAF_CAPACITY or half_size <= BH_MIN_HALF_SIZE:
        stats.leaves += 1
        return _OctreeNode(
            center_x=center_x,
            center_y=center_y,
            center_z=center_z,
            half_size=half_size,
            mass=node_mass,
            com_x=com_x,
            com_y=com_y,
            com_z=com_z,
            indices=indices,
            children=None,
        )

    points = pos[indices]
    octants = (
        (points[:, 0] >= center_x).astype(np.uint8)
        | ((points[:, 1] >= center_y).astype(np.uint8) << 1)
        | ((points[:, 2] >= center_z).astype(np.uint8) << 2)
    )

    child_half = half_size * 0.5
    children: list[_OctreeNode] = []
    for octant in range(8):
        mask = octants == octant
        if not mask.any():
            continue

        child_indices = indices[mask]
        sx = 1.0 if (octant & 1) else -1.0
        sy = 1.0 if (octant & 2) else -1.0
        sz = 1.0 if (octant & 4) else -1.0
        child_cx = center_x + sx * child_half
        child_cy = center_y + sy * child_half
        child_cz = center_z + sz * child_half
        children.append(
            _build_octree_node(
                pos,
                mass,
                child_indices,
                child_cx,
                child_cy,
                child_cz,
                child_half,
                depth + 1,
                stats,
            )
        )

    if not children:
        stats.leaves += 1
        return _OctreeNode(
            center_x=center_x,
            center_y=center_y,
            center_z=center_z,
            half_size=half_size,
            mass=node_mass,
            com_x=com_x,
            com_y=com_y,
            com_z=com_z,
            indices=indices,
            children=None,
        )

    return _OctreeNode(
        center_x=center_x,
        center_y=center_y,
        center_z=center_z,
        half_size=half_size,
        mass=node_mass,
        com_x=com_x,
        com_y=com_y,
        com_z=com_z,
        indices=None,
        children=children,
    )


def _accel_from_tree(
    root: _OctreeNode, target_idx: int, pos: np.ndarray, mass: np.ndarray
) -> tuple[np.ndarray, int]:
    target_x = float(pos[target_idx, 0])
    target_y = float(pos[target_idx, 1])
    target_z = float(pos[target_idx, 2])
    acc_x = 0.0
    acc_y = 0.0
    acc_z = 0.0
    stack = [root]
    visited = 0
    soft2 = SOFTENING * SOFTENING
    theta2 = BH_THETA * BH_THETA
    eps = 1e-9
    tiny = 1e-24

    while stack:
        node = stack.pop()
        visited += 1
        if node.mass <= 0.0:
            continue

        children = node.children
        if not children:
            if node.indices is None:
                continue
            for idx in node.indices:
                if idx == target_idx:
                    continue
                dx = float(pos[idx, 0]) - target_x
                dy = float(pos[idx, 1]) - target_y
                dz = float(pos[idx, 2]) - target_z
                dist_sq = (dx * dx) + (dy * dy) + (dz * dz) + soft2
                inv_r = 1.0 / math.sqrt(dist_sq)
                factor = GRAVITY_G * float(mass[idx]) * inv_r / dist_sq
                acc_x += factor * dx
                acc_y += factor * dy
                acc_z += factor * dz
            continue

        dx = node.com_x - target_x
        dy = node.com_y - target_y
        dz = node.com_z - target_z
        dist_sq_center = (dx * dx) + (dy * dy) + (dz * dz)
        if dist_sq_center <= tiny:
            stack.extend(children)
            continue

        hs = node.half_size
        contains_target = (
            (abs(target_x - node.center_x) <= (hs + eps))
            and (abs(target_y - node.center_y) <= (hs + eps))
            and (abs(target_z - node.center_z) <= (hs + eps))
        )
        size = hs * 2.0

        if (not contains_target) and (
            (size * size) < (theta2 * dist_sq_center)
        ):
            dist_sq = dist_sq_center + soft2
            inv_r = 1.0 / math.sqrt(dist_sq)
            factor = GRAVITY_G * node.mass * inv_r / dist_sq
            acc_x += factor * dx
            acc_y += factor * dy
            acc_z += factor * dz
        else:
            stack.extend(children)

    return np.array([acc_x, acc_y, acc_z], dtype=np.float64), visited
