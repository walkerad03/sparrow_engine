#version 460 core

uniform mat4 u_view_proj;

// Mesh attributes
layout (location = 0) in vec3 in_pos;
layout (location = 1) in vec3 in_normal;
layout (location = 2) in vec2 in_uv;

// Instanced attributes
// mat4 needs 4 attribute slots (3,4,5,6)
layout (location = 3) in mat4 i_model;
layout (location = 7) in vec4 i_color;

out vec3 v_normal;
out vec2 v_uv;
out vec4 v_color;

void main() {
    v_normal = in_normal;
    v_uv = in_uv;
    v_color = i_color;

    gl_Position = u_view_proj * i_model * vec4(in_pos, 1.0);
}
