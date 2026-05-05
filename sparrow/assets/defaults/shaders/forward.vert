#version 460 core

uniform mat4 u_view_proj;
uniform mat4 u_light_space_mat;

// Mesh attributes
layout (location = 0) in vec3 in_pos;
layout (location = 1) in vec3 in_normal;
layout (location = 2) in vec2 in_uv;

// Instanced attributes
// mat4 needs 4 attribute slots (3,4,5,6)
layout (location = 3) in mat4 i_model;
layout (location = 7) in vec4 i_base_color;
layout (location = 8) in vec4 i_material_params;

out vec3 v_world_pos;
out vec4 v_light_space_pos;
out vec3 v_normal;
out vec2 v_uv;
out vec4 v_base_color;
out float v_roughness;
out float v_metallic;
out float v_emissive;

void main() {
    vec4 world_pos = i_model * vec4(in_pos, 1.0);
    v_world_pos = world_pos.xyz;

    // Normal in world space.
    v_normal = normalize(mat3(i_model) * in_normal);

    // Normal bias for shadows: shift the position slightly along the normal
    // to prevent z-fighting (shadow acne) on the surface itself.
    vec3 shadow_world_pos = world_pos.xyz + v_normal * 0.05;
    v_light_space_pos = u_light_space_mat * vec4(shadow_world_pos, 1.0);

    v_uv = in_uv;
    v_base_color = i_base_color;
    v_roughness = i_material_params.x;
    v_metallic = i_material_params.y;
    v_emissive = i_material_params.z;

    gl_Position = u_view_proj * world_pos;
}
