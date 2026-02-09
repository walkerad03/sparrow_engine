# sparrow/graphics/utils/batcher.py
from collections import defaultdict
from typing import Dict, List

import moderngl
import numpy as np

from sparrow.assets import AssetId
from sparrow.graphics.integration import ObjectInstance

INSTANCE_FLOAT_COUNT = 20
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
    ) -> Dict[AssetId, List[ObjectInstance]]:
        """Group a flat list of objects by their Mesh ID."""
        batches = defaultdict(list)
        for obj in objects:
            batches[obj.mesh_id].append(obj)
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
