#version 460 core

in vec2 in_pos;

uniform mat4 u_view_proj;
uniform mat4 u_model;

void main() {
    gl_Position = u_view_proj * u_model * vec4(in_pos, 0.0, 1.0);
}