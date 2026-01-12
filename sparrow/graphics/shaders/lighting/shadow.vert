#version 460 core
in vec3 in_pos;
in vec2 in_uv;

uniform mat4 u_model;
uniform mat4 u_light_view_proj;

out vec3 v_world_pos;
out vec2 v_uv;

void main() {
    vec4 wp = u_model * vec4(in_pos, 1.0);
    v_world_pos = wp.xyz;
    v_uv = in_uv;
    gl_Position = u_light_view_proj * wp;
}
