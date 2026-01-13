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
                        normals[vn_idx] if vn_idx is not None else (0.0, 0.0, 1.0)
                    )
                    u, v = uvs[vt_idx] if vt_idx is not None else (0.0, 0.0)

                    vertices.append(
                        struct.pack("<3f 3f 2f", px, py, pz, nx, ny, nz, u, v)
                    )

        if not vertices:
            raise ValueError(f"No geometry found in OBJ: {path}")

        print(f"[{path}] Load Complete")
        print(
            f"  > Raw Data:   {len(positions)} pos | {len(normals)} norms | {len(uvs)} uvs"
        )
        print(
            f"  > Geometry:   {len(vertices)} vertices ({len(vertices) // 3} triangles)"
        )

        if positions:
            # Calculate bounds to catch scale/rotation issues
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            zs = [p[2] for p in positions]
            print(f"  > Bounds X:   {min(xs):.3f} to {max(xs):.3f}")
            print(f"  > Bounds Y:   {min(ys):.3f} to {max(ys):.3f}")
            print(f"  > Bounds Z:   {min(zs):.3f} to {max(zs):.3f}")
        print("------------------------------------------------")
        print("  > First Face Inspection (Assembled Data):")
        # Check the first 3 vertices (the first triangle)
        for i in range(min(3, len(vertices))):
            # Unpack the 32 bytes back into floats to see what actually got saved
            # Format "3f 3f 2f" = (x,y,z) (nx,ny,nz) (u,v)
            data = struct.unpack("3f 3f 2f", vertices[i])

            p_vals = [f"{v:.2f}" for v in data[0:3]]
            n_vals = [f"{v:.2f}" for v in data[3:6]]
            uv_vals = [f"{v:.2f}" for v in data[6:8]]

            print(f"    Vert {i}: Pos={p_vals}  Norm={n_vals}  UV={uv_vals}")

        print("------------------------------------------------")

        vertex_blob = b"".join(vertices)
        stride = struct.calcsize("<3f3f2f")

        # --- BINARY INSPECTION DEBUG ---
        print(f"--- BINARY DUMP: {path} ---")
        print(f"Total Bytes: {len(vertex_blob)}")
        print(f"Vertex Count: {len(vertices)}")
        print(f"Bytes per Vertex: {len(vertex_blob) / len(vertices)} (Expected: 32.0)")

        # Print the first 2 vertices (64 bytes) in Hex
        # We expect exactly 32 bytes per line if stride is correct
        print("\nFirst 2 Vertices (Hex View):")
        import binascii

        # Take first 64 bytes
        sample = vertex_blob[:64]

        # Print in chunks of 32 bytes (1 vertex per row)
        for i in range(0, len(sample), 32):
            chunk = sample[i : i + 32]
            hex_str = binascii.hexlify(chunk, sep=" ").decode("utf-8")
            print(f"Vert {i // 32}: {hex_str}")

            # Print decoded floats for this chunk to verify content
            try:
                # Unpack assuming the correct layout
                floats = struct.unpack("<3f 3f 2f", chunk)
                print(
                    f"        -> Pos:({floats[0]:.2f}, {floats[1]:.2f}, {floats[2]:.2f}) "
                    f"Norm:({floats[3]:.2f}, {floats[4]:.2f}, {floats[5]:.2f}) "
                    f"UV:({floats[6]:.2f}, {floats[7]:.2f})"
                )
            except struct.error:
                print(
                    "        -> [ERROR] Could not unpack as 32-byte struct (Alignment mismatch?)"
                )

        print("------------------------------------------------")
        # -------------------------------

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
