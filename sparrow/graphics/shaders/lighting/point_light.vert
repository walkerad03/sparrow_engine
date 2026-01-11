#version 330 core

in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;

void main() {
    // Pass UVs directly (0.0 to 1.0)
    v_uv = in_uv;

    // Scale Quad (-0.5 to 0.5) -> Clip Space (-1.0 to 1.0)
    gl_Position = vec4(in_vert * 2.0, 0.0, 1.0);
}