#version 460 core

in GS_OUT {
    vec3 world_pos;
    vec2 uv;
    vec3 tri_normal;
    flat int dominant_axis;
} fs_in;

uniform sampler2D u_albedo;

// 3D images we write to
layout(rgba8, binding = 0) uniform image3D u_vox_albedoOcc; // rgb albedo, a occupancy
layout(rgba16f, binding = 1) uniform image3D u_vox_normal;   // xyz normal in [-1,1] stored as f16

uniform vec3 u_vox_min;
uniform vec3 u_vox_max;
uniform ivec3 u_vox_res;

vec3 worldToVoxN(vec3 w) {
    return (w - u_vox_min) / (u_vox_max - u_vox_min);
}

void main() {
    vec4 a = texture(u_albedo, fs_in.uv);
    if (a.a < 0.01) discard;

    vec3 wn = worldToVoxN(fs_in.world_pos);

    // Determine voxel coordinates based on dominant axis projection used in GS
    ivec3 vc = ivec3(0);

    // Convert normalized to voxel index
    int vx = int(floor(wn.x * float(u_vox_res.x)));
    int vy = int(floor(wn.y * float(u_vox_res.y)));
    int vz = int(floor(wn.z * float(u_vox_res.z)));

    vx = clamp(vx, 0, u_vox_res.x - 1);
    vy = clamp(vy, 0, u_vox_res.y - 1);
    vz = clamp(vz, 0, u_vox_res.z - 1);

    vc = ivec3(vx, vy, vz);

    // Write occupancy + albedo
    // NOTE: multiple fragments can map to same voxel; last-writer wins.
    // For higher quality you’d do atomics or blending in a 3D framebuffer.
    imageStore(u_vox_albedoOcc, vc, vec4(a.rgb, 1.0));
    imageStore(u_vox_normal, vc, vec4(normalize(fs_in.tri_normal), 1.0));
}