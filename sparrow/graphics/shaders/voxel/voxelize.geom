#version 460 core
layout(triangles) in;
layout(triangle_strip, max_vertices = 3) out;

in VS_OUT {
    vec3 world_pos;
    vec2 uv;
} gs_in[];

out GS_OUT {
    vec3 world_pos;
    vec2 uv;
    vec3 tri_normal;
    flat int dominant_axis; // 0 = x, 1 = y, 2 = z
} gs_out;

// World-space voxel volume bounds
uniform vec3 u_vox_min; // world-space min corner
uniform vec3 u_vox_max; // world-space max corner
uniform ivec3 u_vox_res; // (512, 512, 128)

// Convert world position to normalized [0, 1] coordinates within the voxel volume
vec3 worldToVoxN(vec3 w) {
    return (w - u_vox_min) / (u_vox_max - u_vox_min);
}

void main() {
    vec3 p0 = gs_in[0].world_pos;
    vec3 p1 = gs_in[1].world_pos;
    vec3 p2 = gs_in[2].world_pos;

    // Compute triangle normal in world space
    vec3 n = normalize(cross(p1 - p0, p2 - p0));
    vec3 an = abs(n);

    int axis = 2; // default to Z
    if (an.x > an.y && an.x > an.z) axis = 0;
    else if (an.y > an.x && an.y > an.z) axis = 1;

    // Emit the triangle projected onto the dominant axis plane
    //; We output clip-space in [-1,1] using voxel-normalized coords
    for (int i = 0; i < 3; ++i) {
        vec3 wn = worldToVoxN(gs_in[i].world_pos);
        // Reject triangles fully outside volume (cheap coarse test)
        // Note: this is per-vertex; partial triangles still may get clipped by raster.
        if (wn.x < -0.1 || wn.x > 1.1 || wn.y < -0.1 || wn.y > 1.1 || wn.z < -0.1 || wn.z > 1.1) {
            // still emit; raster clip will handle; you can do better culling CPU-side
        }

        // Choose slice and 2D projection:
        // axis=0 (X dominant): project onto YZ plane, layer = x slice
        // axis=1 (Y dominant): project onto XZ plane, layer = y slice
        // axis=2 (Z dominant): project onto XY plane, layer = z slice
        float u = 0.0;
        float v = 0.0;
        int layer = 0;
        
        if (axis == 0) {
            u = wn.y;
            v = wn.z;
            layer = int(floor(wn.x * float(u_vox_res.x)));
        } else if (axis == 1) {
            u = wn.x;
            v = wn.z;
            layer = int(floor(wn.y * float(u_vox_res.y)));
        } else {
            u = wn.x;
            v = wn.y;
            layer = int(floor(wn.z * float(u_vox_res.z)));
        }

        // Clip layer
        if (axis == 0) layer = clamp(layer, 0, u_vox_res.x - 1);
        if (axis == 1) layer = clamp(layer, 0, u_vox_res.y - 1);
        if (axis == 2) layer = clamp(layer, 0, u_vox_res.z - 1);

        gs_out.world_pos = gs_in[i].world_pos;
        gs_out.uv = gs_in[i].uv;
        gs_out.tri_normal = n;
        gs_out.dominant_axis = axis;

        gl_Layer = layer;

        // map u,v (0..1) to clip space (-1..1)
        gl_Position = vec4(u * 2.0 - 1.0, v * 2.0 - 1.0, 0.0, 1.0);
        EmitVertex();
    }

    EndPrimitive();
}