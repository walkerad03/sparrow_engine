#version 330 core

in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;

void main() {
    v_uv = in_vert * 0.5 + 0.5;
    v_uv += in_uv * 0.00000001;

    gl_Position = vec4(in_vert, 0.0, 1.0);
}