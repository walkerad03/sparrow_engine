#version 460 core

in vec2 in_pos;
out vec2 v_uv;

void main() {
    // Fullscreen triangle positions are already in clip space.
    gl_Position = vec4(in_pos, 0.0, 1.0);

    // Convert clip-space (-1..1) to UV (0..1)
    v_uv = in_pos * 0.5 + 0.5;
}
