#version 330 core

layout (location = 0) in vec2 in_pos;

out vec2 v_uv;

void main() {
    vec2 uv = in_pos * 0.5 + 0.5;
    v_uv = vec2(uv.x, 1.0 - uv.y);
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
