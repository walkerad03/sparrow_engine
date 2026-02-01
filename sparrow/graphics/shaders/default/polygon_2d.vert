#version 330 core

in vec2 in_position;
in vec4 in_color;

uniform mat4 u_view_proj;

out vec4 v_color;

void main() {
    v_color = in_color;
    vec4 world_pos = vec4(in_position, 0.0, 1.0);
    gl_Position = u_view_proj * world_pos;
}
