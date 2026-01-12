#version 460 core

in vec3 in_pos;
in vec2 in_uv;

uniform mat4 u_model;

out VS_OUT {
    vec3 world_pos;
    vec2 uv;
} vs_out;

void main() {
    vec4 wp = u_model * vec4(in_pos, 1.0);
    vs_out.world_pos = wp.xyz;
    vs_out.uv = in_uv;

    gl_Position = vec4(0.0); // Not used in voxelization
}