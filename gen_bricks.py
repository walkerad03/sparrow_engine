from pathlib import Path

import numpy as np
from PIL import Image


def generate_maps():
    # Settings for 16x16 Pixel Art
    W, H = 16, 16
    brick_w, brick_h = 8, 4  # Small bricks
    mortar_size = 1  # 1 pixel gap

    # 1. Create Buffers
    albedo = np.zeros((H, W, 3), dtype=np.uint8)
    height_map = np.zeros((H, W), dtype=np.float32)

    # 2. Draw Bricks
    for y in range(0, H, brick_h):
        # Shift every other row by half a brick width
        shift = (brick_w // 2) if (y // brick_h) % 2 == 1 else 0

        for x in range(-brick_w, W, brick_w):
            # Define Brick Rect (with mortar gap)
            bx = x + shift
            by = y
            bw = brick_w - mortar_size
            bh = brick_h - mortar_size

            # Brick Color (Reddish variation)
            col_var = np.random.randint(-20, 20)
            color = [160 + col_var, 50 + col_var, 40 + col_var]

            # Draw logic
            for iy in range(by, by + bh):
                if 0 <= iy < H:
                    for ix in range(bx, bx + bw):
                        if 0 <= ix < W:
                            albedo[iy, ix] = color

                            # Pixel Art Bevel (Simple 1px edge drop)
                            # 1.0 = Flat Top, 0.5 = Bevel Edge
                            dist_x = min(ix - bx, (bx + bw) - 1 - ix)
                            dist_y = min(iy - by, (by + bh) - 1 - iy)

                            if dist_x == 0 or dist_y == 0:
                                height_map[iy, ix] = 0.5  # Edge
                            else:
                                height_map[iy, ix] = 1.0  # Center

    # 3. Mortar Color (Dark Grey)
    # Wherever height is 0 (mortar), set albedo to grey
    mask = height_map < 0.1
    albedo[mask] = [40, 40, 40]

    # 4. Generate Normal Map
    normals = np.zeros((H, W, 3), dtype=np.uint8)

    for y in range(H):
        for x in range(W):
            # Sample neighbors (Clamp to edges)
            h_l = height_map[y, max(0, x - 1)]
            h_r = height_map[y, min(W - 1, x + 1)]
            h_d = height_map[min(H - 1, y + 1), x]
            h_u = height_map[max(0, y - 1), x]

            # Calculate gradients (Aggressive for pixel art pop)
            dx = (h_r - h_l) * 4.0
            dy = (h_u - h_d) * 4.0
            dz = 1.0

            length = np.sqrt(dx * dx + dy * dy + dz * dz)
            nx, ny, nz = dx / length, dy / length, dz / length

            normals[y, x] = [
                int((nx + 1.0) * 127.5),
                int((ny + 1.0) * 127.5),
                int((nz + 1.0) * 127.5),
            ]

    # 5. Save
    out_path = Path("assets/textures")
    out_path.mkdir(parents=True, exist_ok=True)

    Image.fromarray(albedo).save(out_path / "brick.png")
    Image.fromarray(normals).save(out_path / "brick_n.png")
    print(f"Generated 16x16 brick.png and brick_n.png in {out_path}")


if __name__ == "__main__":
    generate_maps()
