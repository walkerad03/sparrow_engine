# sparrow/assets/importers/mesh.py
import struct
from pathlib import Path
from typing import List, Tuple

from sparrow.assets.importers.base import AssetImporter
from sparrow.assets.types import MeshData, VertexLayout


class ObjImporter(AssetImporter):
    def import_file(self, path: Path) -> MeshData:
        positions: List[Tuple[float, float, float]] = []
        normals: List[Tuple[float, float, float]] = []
        uvs: List[Tuple[float, float]] = []
        vertices: List[bytes] = []

        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                tag = parts[0]

                if tag == "v":
                    px, py, pz = map(float, parts[1:4])
                    positions.append((px, py, pz))
                    min_x = min(min_x, px)
                    max_x = max(max_x, px)
                    min_y = min(min_y, py)
                    max_y = max(max_y, py)
                    min_z = min(min_z, pz)
                    max_z = max(max_z, pz)

                elif tag == "vn":
                    nx, ny, nz = map(float, parts[1:4])
                    normals.append((nx, ny, nz))

                elif tag == "vt":
                    u, v = map(float, parts[1:3])
                    uvs.append((u, v))

                elif tag == "f":
                    if len(parts) != 4:
                        raise ValueError(
                            f"Only triangular faces supported in {path}"
                        )

                    for vert in parts[1:4]:
                        v_idx, vt_idx, vn_idx = self._parse_face_vertex(vert)

                        px, py, pz = positions[v_idx]

                        nx, ny, nz = (
                            normals[vn_idx]
                            if vn_idx is not None
                            else (0.0, 1.0, 0.0)
                        )
                        u, v = uvs[vt_idx] if vt_idx is not None else (0.0, 0.0)

                        vertices.append(
                            struct.pack(
                                "<3f 3f 2f", px, py, pz, nx, ny, nz, u, v
                            )
                        )

        if not vertices:
            raise ValueError(f"No geometry found in OBJ: {path}")

        vertex_blob = b"".join(vertices)
        stride = struct.calcsize("<3f3f2f")

        layout = VertexLayout(
            attributes=["in_pos", "in_normal", "in_uv"],
            format="3f 3f 2f",
            stride_bytes=stride,
        )

        return MeshData(
            vertices=vertex_blob,
            vertex_layout=layout,
            aabb=((min_x, min_y, min_z), (max_x, max_y, max_z)),
            indices=None,
        )

    def _parse_index(self, val: str) -> int | None:
        if not val:
            return None
        idx = int(val)
        return idx - 1 if idx > 0 else idx

    def _parse_face_vertex(
        self, token: str
    ) -> Tuple[int, int | None, int | None]:
        parts = token.split("/")
        v = self._parse_index(parts[0])
        vt = (
            self._parse_index(parts[1]) if len(parts) > 1 and parts[1] else None
        )
        vn = (
            self._parse_index(parts[2]) if len(parts) > 2 and parts[2] else None
        )

        # v cannot be None if file is valid, but type checker might complain
        if v is None:
            raise ValueError(f"Invalid vertex index in token: {token}")

        return v, vt, vn
