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

out vec2 v_uv;

void main() {
    v_uv = in_uv;
    
    // Scale
    vec2 pos = in_vert * (u_size / 2.0);
    
    // Rotate
    float s = sin(u_rot);
    float c = cos(u_rot);
    pos = vec2(
        pos.x * c - pos.y * s,
        pos.x * s + pos.y * c
    );
    
    // Translate
    pos += u_pos;
    
    // Project to Screen
    gl_Position = u_matrix * vec4(pos, u_layer, 1.0);
}