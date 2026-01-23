#version 460 core
layout (location=0) in vec3 in_pos;
layout (location=1) in vec3 in_normal;

uniform mat4 u_model;
uniform mat4 u_view_proj;

out vec3 v_normal;
out vec3 v_frag_pos;

void main() {
    vec4 world_pos = u_model * vec4(in_pos, 1.0);
    v_frag_pos = world_pos.xyz;

    mat3 normal_mat = transpose(inverse(mat3(u_model)));
    v_normal = normalize(normal_mat * in_normal);

    gl_Position = u_view_proj * world_pos;
}
