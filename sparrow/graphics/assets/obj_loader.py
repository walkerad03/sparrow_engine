# sparrow/graphics/assets/obj_loader.py
from __future__ import annotations

import struct
from typing import List, Tuple

from sparrow.graphics.assets.types import MeshData, VertexLayout


def load_obj(path: str) -> MeshData:
    """
    Load a Wavefront OBJ file into MeshData.

    Supported:
      - v, vn, vt
      - triangular faces only
      - flat-expanded vertex buffer (no index buffer)

    Raises:
        ValueError: on unsupported or malformed input.
    """
    positions: List[Tuple[float, float, float]] = []
    normals: List[Tuple[float, float, float]] = []
    uvs: List[Tuple[float, float]] = []

    vertices: List[bytes] = []

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

            elif tag == "vn":
                nx, ny, nz = map(float, parts[1:4])
                normals.append((nx, ny, nz))

            elif tag == "vt":
                u, v = map(float, parts[1:3])
                uvs.append((u, v))

            elif tag == "f":
                if len(parts) != 4:
                    raise ValueError("Only triangular faces are supported")

                for vert in parts[1:4]:
                    v_idx, vt_idx, vn_idx = _parse_face_vertex(vert)

                    px, py, pz = positions[v_idx]
                    nx, ny, nz = (
                        normals[vn_idx]
                        if vn_idx is not None
                        else (0.0, 0.0, 1.0)
                    )
                    u, v = uvs[vt_idx] if vt_idx is not None else (0.0, 0.0)

                    vertices.append(
                        struct.pack("<3f 3f 2f", px, py, pz, nx, ny, nz, u, v)
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
            indices=None,
            vertex_layout=layout,
        )


def _parse_index(val: str) -> int | None:
    """
    If positive, convert 1-based to 0-based.
    If negative, keep as is (Python handles relative indexing natively).
    """
    if not val:
        return None
    idx = int(val)
    return idx - 1 if idx > 0 else idx


def _parse_face_vertex(token: str) -> Tuple[int, int | None, int | None]:
    """
    Parse a face vertex token: v/vt/vn or v//vn or v/vt
    OBJ indices are 1-based.
    """
    parts = token.split("/")

    v = _parse_index(parts[0])
    vt = _parse_index(parts[1]) if len(parts) > 1 and parts[1] else None
    vn = _parse_index(parts[2]) if len(parts) > 2 and parts[2] else None

    return v, vt, vn
