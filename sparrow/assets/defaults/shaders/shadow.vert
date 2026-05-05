#version 460 core

uniform mat4 u_light_space_mat;

layout (location = 0) in vec3 in_pos;
layout (location = 3) in mat4 i_model;

void main() {
    gl_Position = u_light_space_mat * i_model * vec4(in_pos, 1.0);
}
