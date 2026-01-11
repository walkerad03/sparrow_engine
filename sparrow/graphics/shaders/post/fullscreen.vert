#version 330 core

layout (location = 0) in vec2 in_vert; // Quad (-0.5 to 0.5)
layout (location = 1) in vec2 in_uv;

out vec2 v_uv;

void main() {
    v_uv = in_uv;
    
    // Scale -0.5..0.5 to -1.0..1.0 to cover full screen
    gl_Position = vec4(in_vert * 2.0, 0.0, 1.0);
}