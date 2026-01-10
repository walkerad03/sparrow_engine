#version 330 core

// Input attributes from the Quad Buffer
in vec2 in_vert;
in vec2 in_uv;

// Global Camera Matrix
uniform mat4 u_matrix;

// Per-Instance Uniforms (Transform)
uniform vec2 u_pos;
uniform vec2 u_size;
uniform float u_rot;
uniform float u_layer; // Z-Index
uniform vec2 u_pivot;   // e.g. (0.5, 0.5) is center
uniform vec4 u_region;  // (u, v, w, h)

uniform float u_skew; // 0.0 = Flat, 0.5 = Standing up

out vec2 v_uv;

void main() {
    vec2 pivot_offset = (vec2(0.5, 0.5) - u_pivot) * u_size;
    
    // Scale
    vec2 pos = in_vert * u_size + pivot_offset;

    vec4 screen_ref = u_matrix * vec4(u_pos, 0.0, 1.0);
    float ndc_x = screen_ref.x / screen_ref.w;

    float total_skew = ndc_x * u_skew;
    float vertical_factor = 0.5 - in_vert.y;

    pos.x += vertical_factor * u_size.y * total_skew;
    
    // Rotate
    float s = sin(u_rot);
    float c = cos(u_rot);
    mat2 rot_mat = mat2(c, -s, s, c);
    pos = rot_mat * pos;
    
    // Translate
    pos += u_pos;
    
    // Project to Screen
    gl_Position = u_matrix * vec4(pos, u_layer, 1.0);

    v_uv = vec2(
        u_region.x + (in_uv.x * u_region.z),
        u_region.y + (in_uv.y * u_region.w)
    );
}