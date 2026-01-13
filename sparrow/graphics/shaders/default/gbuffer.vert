#version 460

in vec3 in_pos;
in vec3 in_normal;
in vec2 in_uv;

uniform mat4 u_model;
uniform mat4 u_view_proj;

out vec3 v_normal_ws;
out vec2 v_uv;

void main() {
    vec4 world_pos = u_model * vec4(in_pos, 1.0);

    mat3 normal_matrix = transpose(inverse(mat3(u_model)));
    v_normal_ws = mat3(u_model) * in_normal;
    
    v_uv = in_uv;
    gl_Position = u_view_proj * world_pos;
}
