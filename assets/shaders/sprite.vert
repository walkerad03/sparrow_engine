#version 330 core

// Input attributes from the Quad Buffer
in vec2 in_vert;
in vec2 in_uv;

// Global Camera Matrix
uniform mat4 u_matrix;

// Per-Instance Uniforms (Transform)
uniform vec3 u_pos;
uniform vec2 u_size;
uniform float u_rot;
uniform float u_layer; // Z-Index
uniform vec2 u_pivot;   // e.g. (0.5, 0.5) is center
uniform vec4 u_region;  // (u, v, w, h)

uniform float u_skew; // 0.0 = Flat, 1.0 = Standing up

out vec2 v_uv;

void main() {
    vec2 pivot_offset = (vec2(0.5, 0.5) - u_pivot) * u_size;
    vec2 local_pos_2d = in_vert * u_size + pivot_offset;

    // Rotate
    float s = sin(u_rot);
    float c = cos(u_rot);
    mat2 rot_mat = mat2(c, -s, s, c);
    local_pos_2d = rot_mat * local_pos_2d;

    // Convert to 3d space
    vec3 local_pos_3d = vec3(local_pos_2d, 0.0);

    // Standing up logic
    float angle_x = u_skew * 1.57079632679;

    float sx = sin(angle_x);
    float cx = cos(angle_x);

    mat3 rot_x_mat = mat3(
        1.0, 0.0, 0.0,
        0.0,  cx,  -sx, // Column 2
        0.0, sx,  cx  // Column 3
    );

    vec3 standing_pos = rot_x_mat * local_pos_3d;
    vec3 final_pos = standing_pos + u_pos;

    gl_Position = u_matrix * vec4(final_pos, 1.0);
    gl_Position.z += u_layer * 0.001;

    v_uv = vec2(
        u_region.x + (in_uv.x * u_region.z),
        u_region.y + (in_uv.y * u_region.w)
    );
}