# sparrow/graphics/utils/batcher.py
from collections import defaultdict
from typing import Dict, List

import moderngl
import numpy as np

from sparrow.assets import AssetId
from sparrow.graphics.integration import ObjectInstance

BatchKey = tuple[AssetId, AssetId | None]

INSTANCE_FLOAT_COUNT = 24
INSTANCE_STRIDE = INSTANCE_FLOAT_COUNT * 4


class RenderBatcher:
    """
    Helper to manage instanced rendering buffers and object grouping.
    """

    def __init__(self, ctx: moderngl.Context, initial_capacity: int = 10000):
        self.ctx = ctx
        self.capacity = initial_capacity
        self.buffer: moderngl.Buffer | None = self.ctx.buffer(
            reserve=self.capacity * INSTANCE_STRIDE,
            dynamic=True,
        )

        self._cpu_buffer = np.zeros(
            (self.capacity, INSTANCE_FLOAT_COUNT), dtype="f4"
        )

    def group_objects(
        self, objects: List[ObjectInstance]
    ) -> Dict[BatchKey, List[ObjectInstance]]:
        """Group a flat list of objects by Mesh ID and albedo texture."""
        batches = defaultdict(list)
        for obj in objects:
            batches[(obj.mesh_id, obj.albedo_id)].append(obj)
        return batches

    def group_columns(
        self,
        mesh_ids: np.ndarray,
        albedo_ids: np.ndarray,
    ) -> Dict[BatchKey, np.ndarray]:
        """Group columnar mesh/albedo arrays and return index slices per batch."""
        if mesh_ids.size == 0:
            return {}

        order = np.lexsort((albedo_ids, mesh_ids))
        mesh_sorted = mesh_ids[order]
        albedo_sorted = albedo_ids[order]

        split_at = (
            np.flatnonzero(
                (mesh_sorted[1:] != mesh_sorted[:-1])
                | (albedo_sorted[1:] != albedo_sorted[:-1])
            )
            + 1
        )
        starts = np.concatenate((np.array([0], dtype=np.int64), split_at))
        ends = np.concatenate(
            (split_at, np.array([order.size], dtype=np.int64))
        )

        batches: Dict[BatchKey, np.ndarray] = {}
        for start, end in zip(starts.tolist(), ends.tolist()):
            mesh_id = int(mesh_sorted[start])
            albedo_raw = int(albedo_sorted[start])
            albedo_id = None if albedo_raw < 0 else albedo_raw
            batches[(mesh_id, albedo_id)] = order[start:end]

        return batches

    def prepare_instance_data(
        self, instances: List[ObjectInstance], transforms: np.ndarray
    ) -> None:
        """Pack instance data into the GPU buffer."""
        count = len(instances)
        if count == 0:
            return

        if count > self.capacity:
            self._resize(count)

        # TODO: Make ObjectInstance store precomputed numpy array
        for i, obj in enumerate(instances):
            # Model Matrix (column major)
            self._cpu_buffer[i, 0:16] = transforms[
                obj.transform_index
            ].T.reshape(16)
            # Color (RGBA)
            self._cpu_buffer[i, 16] = obj.color[0]
            self._cpu_buffer[i, 17] = obj.color[1]
            self._cpu_buffer[i, 18] = obj.color[2]
            self._cpu_buffer[i, 19] = obj.color[3]
            # Material parameters
            self._cpu_buffer[i, 20] = obj.roughness
            self._cpu_buffer[i, 21] = obj.metallic
            self._cpu_buffer[i, 22] = obj.emissive
            self._cpu_buffer[i, 23] = 0.0

        if self.buffer is None:
            return

        data_view = self._cpu_buffer[:count]
        self.buffer.write(data_view.tobytes())

    def prepare_instance_data_columns(
        self,
        indices: np.ndarray,
        transforms: np.ndarray,
        colors: np.ndarray,
        roughness: np.ndarray,
        metallic: np.ndarray,
        emissive: np.ndarray,
    ) -> None:
        count = int(indices.size)
        if count == 0:
            return

        if count > self.capacity:
            self._resize(count)

        self._cpu_buffer[:count, 0:16] = (
            transforms[indices].transpose(0, 2, 1).reshape(count, 16)
        )
        self._cpu_buffer[:count, 16:20] = colors[indices]
        self._cpu_buffer[:count, 20] = roughness[indices]
        self._cpu_buffer[:count, 21] = metallic[indices]
        self._cpu_buffer[:count, 22] = emissive[indices]
        self._cpu_buffer[:count, 23] = 0.0

        if self.buffer is None:
            return

        data_view = self._cpu_buffer[:count]
        self.buffer.write(data_view.tobytes())

    def _resize(self, new_min_capacity: int) -> None:
        """Double capacity until data fits."""
        new_cap = max(new_min_capacity, self.capacity * 2)
        if self.buffer is None:
            return
        self.buffer.orphan(new_cap * INSTANCE_STRIDE)
        self._cpu_buffer = np.zeros((new_cap, INSTANCE_FLOAT_COUNT), dtype="f4")
        self.capacity = new_cap

    def release(self) -> None:
        if self.buffer is not None:
            self.buffer.release()
            self.buffer = None
