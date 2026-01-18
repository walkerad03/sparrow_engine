#version 460 core

in vec2 in_pos;
out vec2 v_uv;

void main() {
    // NDC -> UV
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
