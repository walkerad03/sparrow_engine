#version 330 core

in vec3 in_pos;
in vec2 in_uv;

uniform mat4 u_view_proj;
uniform mat4 u_model;

out vec2 v_uv;

void main() {
    v_uv = in_uv;

    gl_Position = u_view_proj * u_model * vec4(in_pos, 1.0);
}
