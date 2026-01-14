#version 460 core

in vec3 in_pos;
in vec3 in_normal;

uniform mat4 u_view_proj;
uniform mat4 u_model;

out vec3 v_world_pos;
out vec3 v_normal;

void main() {
    vec4 world_pos = u_model * vec4(in_pos, 1.0);
    v_world_pos = world_pos.xyz;
    v_normal = mat3(transpose(inverse(u_model))) * in_normal;
    gl_Position = u_view_proj * world_pos;
}