#version 460 core
layout (location=0) in vec3 in_pos;

uniform mat4 u_model;
uniform mat4 u_view_proj;

void main() {
    gl_Position = u_view_proj * u_model * vec4(in_pos, 1.0);
}
